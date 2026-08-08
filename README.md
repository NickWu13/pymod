# pymod

> **[中文文档 → README.zh-CN.md](README.zh-CN.md)**

Compile a **restricted Python DSL** into Minecraft Java Edition artifacts:

- **Data Pack** (`--target datapack`) — `pack.mcmeta`, tags, advancements, mcfunctions
- **KubeJS** (`--target kubejs`) — server scripts (stage 4)
- **Fabric Java Mod** (`--target fabric`) — a compilable Gradle project (stage 5)

pymod is a *low-code mod compiler*, not a Python runtime: your `.py` file is
parsed and validated, lowered to a target-agnostic IR, checked against the
chosen target's capability matrix, and then generated. Anything unsupported is
a hard error with a file/line location — never a silent drop.

## Quickstart

```bash
pip install -e .            # stdlib-only toolchain, no third-party deps
pymod check examples/chaos.py
pymod check examples/chaos.py --target datapack
pymod generate examples/chaos.py --target datapack --out out/datapack --pack-format <N>
pymod generate examples/chaos.py --target kubejs  --out out/kubejs
pymod generate examples/chaos.py --target fabric  --out out/fabric
```

## Pipeline

```
.pydsl source -> ast whitelist (parser) -> IR (builder) -> checker -> codegen
```

- **parser** rejects any syntax outside the DSL subset (`docs/dsl.md`).
- **builder** lowercases semantics: known events/actions, argument counts/types,
  id resolution, duplicate registrations.
- **checker** runs *before* codegen and reports every per-target capability
  problem at once.
- **generators** only ever see checked IR.

## Status

| Phase | Status |
|---|---|
| 0: version research (MC 26.2, real Fabric deps) | done — profile in `src/pymod/gameprofiles.json` |
| 1: scaffold + errors + IR + capability | done |
| 2: DSL parser + checker | done |
| 3: Data Pack generator | done (MVP subset; pack_format 107 verified) |
| 4: KubeJS generator | done (MVP subset) |
| 5: Fabric Java Mod generator | done (compiles vs real 26.2 deps; events/actions pending) |
| 6: tests / examples / docs / CI | done |

MC 26.2 facts confirmed from Mojang's shipped client jar (2026-08-06):
data pack format **107**, resource pack format **88**, released 2026-06-16,
Fabric Loader `0.19.3`, Fabric API `0.156.0+26.2`, Java `25`. 26.x is the
**post-obfuscation era**: Mojang ships a named (de-obfuscated) jar, so Yarn /
Mojang mapping files don't exist — the Fabric target uses an identity
intermediary mapping and generates Java against the real Mojang names
(verified: the generated project compiles with `gradle build`, producing a
distributable mod jar). Loom `1.17.19`, Gradle `9.7.0`.

## Development

```bash
python -m pytest tests/ -v            # fast suite (36 tests)
PYMOD_RUN_FABRIC_BUILD=1 pytest -q tests/test_fabric_build.py   # real-deps compile check (slow)
```
