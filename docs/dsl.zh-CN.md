# pymod DSL 参考（中文）

一个 pymod 文件是**合法的 Python，但只会被解析，绝不会被执行**。只接受下面列出的子集，除此之外的任何写法都是带行号的 `ParseError`。

## 语法示例

```python
from pymod import mod                    # 唯一允许的 import

mod(id="chaoscube", name="混沌立方", version="1.0.0", description="示例")

register("tag",    "blocks/magic", values=["minecraft:stone", "minecraft:dirt"])
register("item",   "ruby", max_stack=64)
register("block",  "ruby_ore", hardness=3.0)

@mod.on("player.use_item")               # 事件种类
def on_stick(ctx):                       # 参数必须恰好是 ctx
    count = 1                            # 常量赋值
    if ctx.item == "minecraft:stick":    # 简单比较
        ctx.send_message("你用木棍点了点！")   # ctx.<动作>(字面量, ...)
        ctx.give_item("minecraft:diamond", count)
    ctx.play_sound("minecraft:block.note_block.pling", 0, 0, 0, 0.5, 1.0)
```

## 顶层允许

- `from pymod import mod`
- `mod(id=..., name=..., version=..., description=...)`
  - `id` 必须是小写 `[a-z0-9_.-]` 且以字母开头；`id`/`name`/`version` 必填。
- `register(kind, name, **props)`：

  | kind | name 形态 | props |
  |---|---|---|
  | `item` | `ruby` | `max_stack: int`、`has_glint: bool` |
  | `block` | `ruby_ore` | `hardness: float`、`transparent: bool` |
  | `tag` | `blocks/magic` 或 `items/foo` | `values: [id, ...]` |

- `@mod.on("事件种类")` 处理器。事件种类与 `ctx` 可用参数：

  | 事件 | ctx 参数 |
  |---|---|
  | `player.use_item` | `player`、`item` |
  | `player.right_click_block` | `player`、`block`、`pos` |
  | `entity.killed` | `entity`、`killer` |
  | `block.broken` | `player`、`block`、`pos` |
  | `advancement.granted` | `player`、`advancement` |

## 处理器内允许

- `ctx.<动作>(位置字面量参数...)`：

  | 动作 | 参数 |
  |---|---|
  | `send_message` | `message: str` |
  | `give_item` | `item: id`、`count: int = 1` |
  | `set_block` | `x, y, z: int`、`block: id` |
  | `teleport` | `target: str`、`x, y, z: float` |
  | `spawn_particle` | `effect: id`、`x, y, z: float`、`count: int = 1` |
  | `play_sound` | `sound: id`、`x, y, z: float`、`volume, pitch: float` |
  | `grant_advancement` | `advancement: id` |

- 条件：只能是**单个比较**（`== != < <= > >=`）或 `and` 连接；`else` 仅在条件恰为一个可取反的比较时支持（生成取反条件）。
- 处理器内允许**常量赋值**（`count = 1`），赋值后的变量可用作后续参数。
- 事件参数（`ctx.<参数>`）可用于条件左侧。
- 处理器内允许开头的一个 docstring（会被忽略）。

## MVP 明确不支持（一律精确行号报错，绝不静默忽略）

- 除 `from pymod import mod`（或 `from pymod import *`）外的任何 import。
- 自定义函数、类、lambda、列表推导式。
- 条件里的 `or` / `not` / 括号 / 链式比较（`a < b < c`）/ 嵌套 `if`。
- 处理器里的 `return` / `for` / `while`。
- 字符串格式化 / 拼接；除 `ctx.<动作>(...)` 外的任何调用。
- `ctx` 动作的关键字参数。

遇到以上任一项，pymod 都会在**确切的 `文件:行:列`** 上拒绝该文件并给出提示。