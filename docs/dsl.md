# pymod DSL (MVP)

A pymod file is valid Python that is **parsed, never executed**. Only the
subset below is accepted; everything else is a `ParseError` with a line number.

## Grammar

```python
from pymod import mod                    # the only allowed import

mod(id="chaoscube", name="Chaos Cube", version="1.0.0", description="...")

register("tag",   "blocks/magic", values=["minecraft:stone", "minecraft:dirt"])
register("item",  "ruby", max_stack=64)
register("block", "ruby_ore", hardness=3.0)

@mod.on("player.use_item")               # event kind
def on_stick(ctx):                       # exactly one parameter, named ctx
    count = 1                            # literal assignment
    if ctx.item == "minecraft:stick":    # simple comparison
        ctx.send_message("hi")           # ctx.<action>(literal, ...)
        ctx.give_item("minecraft:diamond", count)
    ctx.play_sound("minecraft:block.note_block.pling", 0, 0, 0, 0.5, 1.0)
```

## Allowed at top level

- `from pymod import mod`
- `mod(id=..., name=..., version=..., description=...)` — `id` must be
  `[a-z0-9_.-]` starting with a letter; `id`/`name`/`version` required.
- `register(kind, name, **props)` — kinds and props:

  | kind | name form | props |
  |---|---|---|
  | `item` | `ruby` | `max_stack: int`, `has_glint: bool` |
  | `block` | `ruby_ore` | `hardness: float`, `transparent: bool` |
  | `tag` | `blocks/magic` or `items/foo` | `values: [id, ...]` |

- `@mod.on("event.kind")` handlers. Event kinds:
  `player.use_item`, `player.right_click_block`, `entity.killed`,
  `block.broken`, `advancement.granted`.
  Event parameters (reference via `ctx.<param>` in conditions):
  `use_item` → `player`, `item`; `right_click_block`/`block.broken` → `player`,
  `block`, `pos`; `entity.killed` → `entity`, `killer`;
  `advancement.granted` → `player`, `advancement`.

## Allowed inside a handler

- `ctx.<action>(...)` positional literal args. Actions:

  | action | args |
  |---|---|
  | `send_message` | `message: str` |
  | `give_item` | `item: id`, `count: int = 1` |
  | `set_block` | `x, y, z: int`, `block: id` |
  | `teleport` | `target: str`, `x, y, z: float` |
  | `spawn_particle` | `effect: id`, `x, y, z: float`, `count: int = 1` |
  | `play_sound` | `sound: id`, `x, y, z: float`, `volume, pitch: float` |
  | `grant_advancement` | `advancement: id` |

- `if ctx.<param> == "literal":` — conditions may only be a single comparison
  (`== != < <= > >=`) or `and`-chained comparisons; literals are allowed on the
  left for `literal OP literal` (use sparingly).
- `else:` — supported only when the `if` condition is exactly one comparison
  (it becomes the negated condition).
- assignment of literal values (`count = 1`) usable as later arguments.
- a leading docstring inside a handler is ignored.

## Not allowed in MVP (documented limits)

- `import` of anything except `from pymod import mod`
- custom functions, classes, lambdas, comprehensions
- `or` / `not` / parentheses in conditions; chained comparisons; nested `if`
- `return`, `for`, `while`
- string formatting / concatenation; calls other than `ctx.<action>(...)`
- keyword arguments on `ctx` actions

When you hit one of these, pymod rejects the file at the exact line with a
hint — it never silently ignores unsupported syntax.
