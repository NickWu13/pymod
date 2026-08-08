# Examples

Each file is a pymod DSL source — *parsed, never executed*.

| file | purpose | best demo |
|---|---|---|
| `chaos.py` | the main example: tag/item/block registrations + a `player.use_item` handler with an `if` guard | `pymod check chaos.py -t datapack`; `pymod generate chaos.py -t datapack -o out` |
| `kubejs_demo.py` | the KubeJS-friendly subset (no actions KubeJS MVP rejects) | `pymod generate kubejs_demo.py -t kubejs -o out` |
| `fabric_demo.py` | registrations-only, compiles against real 26.2 deps | `pymod generate fabric_demo.py -t fabric -o out` then `python tools/build_fabric.py out build` |
| `ifelse.py` | demonstrates a *documented difference*: an `if`/`else` pair of `ctx.item` guards is rejected by the datapack (single-advancement predicate) but expressible in KubeJS(JS `if`) | `pymod generate ifelse.py -t kubejs -o out` succeeds; `-t datapack` fails with `datapack-unsupported-guard` |

`chaos.py` also shows the honest per-target split: `pymod check chaos.py -t kubejs`
rejects `ctx.play_sound` (KubeJS MVP can't emit it), and `-t fabric` rejects all
events/actions (not yet proven to compile).