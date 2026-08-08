# pymod 目标与能力矩阵（中文）

每个目标都从**同一份已校验的 IR** 开始。`src/pymod/ir/capability.py` 是「这个目标能表达什么」的唯一权威；矩阵之外的写法，`pymod check --target <目标>` 会用**精确的错误码与位置**拒绝。

## 能力矩阵总表

| 能力 | datapack | kubejs | fabric |
|---|---|---|---|
| 注册 item/block | 仅元数据 | 仅元数据 | ✅ 真实注册（已验证编译） |
| 注册 tag | ✅ 真实 tag JSON | ✅ `ServerEvents.tags` | ✅ 资源 JSON |
| 事件 `player.use_item` | ✅* | ✅ `ItemEvents.rightClicked` | ⛔ 未验证，拒绝 |
| 事件 `player.right_click_block` | ✅* | ✅ `BlockEvents.rightClicked` | ⛔ 未验证，拒绝 |
| 事件 `block.broken` | ⛔ | ✅ `BlockEvents.broken` | ⛔ 未验证，拒绝 |
| 事件 `entity.killed` | ⛔ | ⛔ | ⛔ 未验证，拒绝 |
| 事件 `advancement.granted` | ⛔ | ⛔ | ⛔ 未验证，拒绝 |
| 动作 `send_message` / `give_item` | ✅ | ✅ | ⛔ |
| 动作 `set_block` | ✅ | ✅ | ⛔ |
| 动作 `teleport` / `spawn_particle` / `play_sound` | ✅ | ⛔ | ⛔ |
| 动作 `grant_advancement` | ✅ | ⛔ | ⛔ |

> `*` datapack 的这两个事件用 `item_used_on_block` 进度触发来近似模拟，奖励函数**每个玩家单次触发**。

---

## Data Pack（已实现，MVP）

- 产出 `pack.mcmeta`、`data/<modid>/{tags,advancement,function}/...` 与 `mod_manifest.json`。
- `player.use_item` / `player.right_click_block` 用 `minecraft:item_used_on_block` 进度触发驱动奖励函数；奖励函数**每个玩家只触发一次**（文档化限制）。
- 一个处理器**最多只能带一条 `ctx.item == / != ...` 条件**，它会成为进度的谓词；其余守卫被拒绝（见 `examples/ifelse.py`）。
- `item`/`block` 注册仅为元数据——单纯数据包无法定义新游戏内容。
- `pack_format` 读自游戏档案（`--game`）；26.2 已核验值为 **107**（资源 **88**），来源是 Mojang 发布的 client jar。`--pack-format` 保留为显式覆盖。

## KubeJS（已实现，MVP）

- 产出 `server_scripts/<modid>.js`（KubeJS 从整合包的 `server_scripts/` 加载）。
- 事件：`player.use_item` → `ItemEvents.rightClicked`、`player.right_click_block` → `BlockEvents.rightClicked`、`block.broken` → `BlockEvents.broken`。三者都保证有 `event.player`，而每条生成的 action 都依赖它。
- 动作：`send_message` → `event.player.tell(...)`、`give_item` → `event.player.give(Item.of(...))`、`set_block` → `event.server.runCommandSilent("setblock x y z block")`（绝对坐标，MVP 简化，与 datapack 一致）。
- 条件：`ctx.item` / `ctx.block` 的任意比较映射为 JS `if`；**单比较的 if/else 在 kubejs 可表达**（datapack 反而拒绝——见 `examples/ifelse.py`）。
- `tag` 注册变成 `ServerEvents.tags` 的追加，命名空间化到 mod（`chaoscube:items/rare`），与 datapack 的 tag 路径布局一致。

## Fabric（已实现，阶段 5）

- 产出标准 Fabric Loom 工程，并**在真实 26.2 依赖下构建成功**（loader `0.19.3`、fabric-api `0.156.0+26.2`、Loom `1.17.19`、Gradle `9.7.0`、Java release **25**）——由 `tools/build_fabric.py <out> build` 实际编译验证。
- **26.x 是「混淆后时代」**：Mojang 发布的是命名（已解混淆）client jar，所以 26.2 没有 Yarn，也没有 Mojang 官方映射文件；Fabric 的 intermediary 是一份空恒等映射（`v1 official intermediary`）。Loom 还需要 `named` 列，因此生成器附带一张三列恒等映射（`mappings/identity.tiny`），并禁用 `remapSourcesJar`（源码本来就是 Mojang 名）。
- `tag` 注册 → `src/main/resources/data/<modid>/tags/...` 资源 JSON（零 API 风险）。
- `item`/`block` 注册 → `Registry.register(BuiltInRegistries.ITEM, Identifier.fromNamespaceAndPath(...), ...)` 等——签名取自对 26.2 client jar 的 `javap`，并**已验证可编译**。
- 事件/动作由能力矩阵门控，直到每条 Java 映射在编译循环中被证实；未验证的一律明确拒绝。