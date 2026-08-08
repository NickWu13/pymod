# Output targets

Every target starts from the same checked IR. The capability matrix in
`src/pymod/ir/capability.py` is the single authority on what each target can
express; anything else is rejected by `pymod check --target <t>` with a precise
code and location.

| capability | datapack | kubejs | fabric |
|---|---|---|---|
| register item/block | metadata only | metadata only | yes |
| register tag | yes (real tag JSON) | yes (ServerEvents.tags) | yes |
| event player.use_item | yes* | yes (ItemEvents.rightClicked) | yes |
| event player.right_click_block | yes* | yes (BlockEvents.rightClicked) | yes |
| event entity.killed | no | no (deferred) | yes |
| event block.broken | no | yes (BlockEvents.broken) | yes |
| event advancement.granted | no | no | yes |
| action send_message/give_item | yes | yes | yes |
| action set_block | yes | yes (runCommandSilent, absolute coords) | yes |
| action teleport/particle/sound | yes | no (deferred) | yes |
| action grant_advancement | yes | no | yes |

## Data Pack (implemented, MVP)

- Emits `pack.mcmeta`, `data/<modid>/{tags,advancement,function}/...` and a
  `mod_manifest.json`.
- `player.use_item` / `player.right_click_block` are simulated with the
  `item_used_on_block` advancement trigger whose reward function runs the
  actions. Reward functions fire **once per player**.
- A handler may carry at most one `ctx.item == / != ...` condition; it becomes
  the advancement predicate. Other guards are rejected (see `examples/ifelse.py`).
- `item`/`block` registrations are metadata only — a data pack alone cannot
  define new game content.
- `pack_format` is read from the game profile (`--game`); 26.2's verified value
  is **107** (data) / **88** (resource), sourced from Mojang's shipped client jar.
  `--pack-format` remains available as an explicit override.

## KubeJS (implemented, MVP)

- Emits `server_scripts/<modid>.js` (loaded by KubeJS from a pack's
  `server_scripts/` folder).
- Events: `player.use_item` → `ItemEvents.rightClicked`, `player.right_click_block`
  → `BlockEvents.rightClicked`, `block.broken` → `BlockEvents.broken`. All three
  guarantee an `event.player`, which every emitted action relies on.
- Actions: `send_message` → `event.player.tell(...)`, `give_item` →
  `event.player.give(Item.of(...))`, `set_block` →
  `event.server.runCommandSilent("setblock x y z block")` (absolute coords, same
  MVP caveat as the datapack).
- Conditions: any `ctx.item` / `ctx.block` comparison maps to a JS `if`;
  if/else with a single comparison is expressible (unlike the datapack).
- `tag` registrations become `ServerEvents.tags` additions namespaced to the mod
  (`chaoscube:items/rare`), matching the datapack tag path layout.

## Fabric (implemented, stage 5)

- Emits a standard Fabric Loom Gradle project that **builds successfully against
  the real 26.2 dependency set** (loader `0.19.3`, fabric-api `0.156.0+26.2`,
  Loom `1.17.19`, Gradle `9.7.0`, Java release `25`) — verified by actually
  compiling the generated project with `tools/build_fabric.py <out> build`
  (`pymod generate` assumes, and the compile loop confirms).
- 26.x is the **post-obfuscation era**: Mojang ships a *named* (de-obfuscated)
  client jar, so `officialMojangMappings()`/yarn do not exist for 26.2. Fabric's
  intermediary for 26.x is an empty identity map (`v1 official intermediary`).
  Loom additionally needs a `named` column, so the generator writes a three-column
  identity mapping (`mappings/identity.tiny`) and `remapSourcesJar` is disabled
  (sources are already in Mojang names).
- `tag` registrations become resource JSON files under
  `src/main/resources/data/<modid>/tags/...` (zero API risk).
- `item`/`block` registrations become `Registry.register(BuiltInRegistries.ITEM,
  Identifier.fromNamespaceAndPath(...), ...)` etc. — signatures taken from
  `javap` on the shipped 26.2 client jar and proven to compile.
- Events/actions are gated by the capability matrix until each Java mapping is
  proven in the build loop; unverified ones are rejected explicitly.
