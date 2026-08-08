# pymod: design & stage log

## Ideas in one paragraph

pymod compiles a *restricted* Python DSL into Minecraft targets instead of
running Python.  Every user file is parsed by CPython's `ast`, reduced to a
target-agnostic IR by a builder, validated by a per-target capability
checker, and only then rendered by a code generator.  Anything the DSL or a
target cannot express is a hard, located error — never a silent drop.

## Pipeline (why each layer exists)

```
source            parser (ast whitelist) → Program      fails on foreign syntax
Program           builder (IR)           → ModSpec      fails on bad semantics
ModSpec+target    checker (capability)   → Report       lists every unsupported item
approved IR       generators             → files        only ever see checked IR
```

- **parser**: whitelist-only. Rejects any top-level construct or handler
  statement outside the documented grammar (`docs/dsl.md`).
- **builder**: semantic validation — known events/actions, argument arity and
  types, id resolution (`minecraft:` default namespace, modid for registered
  names), duplicate registrations — and reduces `if`/`else` into conjunctive
  `Guard` tuples on each action, so generators never re-understand Python.
- **checker**: per-target capability matrix (`capability.py` is the single
  authority). Collects *all* problems at once.
- **generators**: datapack (advancements+mcfunctions), kubejs (server_scripts),
  fabric (Gradle project).

## Version strategy

All version-sensitive facts are data, in `src/pymod/gameprofiles.json`
(game id, pack formats, fabric loader/api/loom/gradle, mapping note).  Generators
never hardcode a version.  The tool pins **one** game version — today MC 26.2.

### 26.2 facts (verified 2026-08, from Mojang's shipped client jar + Fabric meta)
- released 2026-06-16; data-pack format **107**, resource format **88**.
- Fabric Loader `0.19.3`, Fabric API `0.156.0+26.2`, Loom `1.17.19`,
  Gradle `9.7.0` (Gradle ≥9 required to run on JDK 26), Java release `25`.
- **Post-obfuscation:** Mojang ships a *named* (de-obfuscated) client jar
  (0 `class_####`). Yarn and Mojang mapping files don't exist for 26.2;
  Fabric's intermediary `26.2` is an empty identity map. Loom is fed a
  generated three-column identity tiny; `remapSourcesJar` is disabled.

## The stages

0. version research — done (profile data above).
1. scaffold + errors + IR + capability — done.
2. DSL parser + checker — done.
3. DataPack generator — done (MVP event model; `docs/targets.md`).
4. KubeJS generator — done (MVP event/action subset).
5. Fabric generator — done for registrations: the generated project compiles
   against real 26.2 deps (`tools/build_fabric.py out build` → `BUILD SUCCESSFUL`,
   distributable jar). Events/actions remain gated until each mapping is proven
   in the same loop.
6. tests / examples / docs / CI — done (golden + error-contract + gated
  real-build tests, CI workflow, docs, .gitignore).

## Verification philosophy

Every stage ships with a test. Golden tests lock exact emitted bytes. The
Fabric claim ("generated Java compiles against real deps") is verified by an
opt-in integration test running a real Gradle build; a code generator may only
emit an API surface that has been proven to compile, and anything unproven is
rejected explicitly by the capability matrix.