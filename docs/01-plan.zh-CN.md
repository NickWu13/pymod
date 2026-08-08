# pymod：设计与阶段日志（中文）

## 一句话

pymod 编译一个*受限*的 Python DSL 去生成 Minecraft 目标，而不是运行 Python。每个用户文件都由 CPython 的 `ast` 解析、由 builder 降级为与目标无关的 IR、由按目标的能力检查器校验，最后才由代码生成器渲染。DSL 或目标表达不了的任何东西都是带位置的硬错误——绝不静默丢弃。

## 管线（每一层为什么存在）

```
source            parser 白名单   → Program      陌生语法直接失败
Program           builder(IR)     → ModSpec      语义错误直接失败
ModSpec+target    checker(能力)   → Report       一次列全不支持项
approved IR       generators      → 文件         只能见到已校验的 IR
```

- **parser**：只放白名单。任何顶层结构或处理器语句不在文档化语法（`docs/dsl.md`）内即拒绝。
- **builder**：语义校验——事件/动作是否已知、参数数量与类型、ID 解析（`minecraft:` 缺省命名空间，用 modid 补注册名）、重复注册；并把 `if`/`else` 归约成挂在每个动作上的合取 `Guard` 元组，生成器从此不必再理解 Python。
- **checker**：按目标读能力矩阵（`capability.py` 是唯一权威）。一次枚举全部问题。
- **generators**：datapack（进度 + mcfunction）、kubejs（server_scripts）、fabric（Gradle 工程）。

## 版本策略

所有版本敏感信息都是数据，集中在 `src/pymod/gameprofiles.json`（游戏 id、数据包格式、fabric loader/api/loom/gradle、映射说明）。生成器绝不硬编码版本号。工具**只固定一枚版本**——今天锁定 **MC 26.2**。

### 26.2 已核验事实（2026-08，取自 Mojang 官方 client jar + Fabric meta）
- 2026-06-16 发布；数据包格式 **107**、资源包格式 **88**。
- Fabric Loader `0.19.3`、Fabric API `0.156.0+26.2`、Loom `1.17.19`、
  Gradle `9.7.0`（Gradle ≥9 才能在 JDK 26 上跑）、Java release `25`。
- **混淆后时代**：Mojang 发布命名（已解混淆）client jar（0 个 `class_####`）。
  Yarn 与 Mojang 映射文件对 26.2 都不存在；Fabric 的 intermediary `26.2` 是空恒等映射。
  Loom 挂一张生成的三列恒等 tiny；`remapSourcesJar` 禁用。

## 六个阶段

0. 版本研究 —— 完成（上文档案数据）。
1. 脚手架 + errors + IR + 能力矩阵 —— 完成。
2. DSL parser + checker —— 完成。
3. Data Pack 生成器 —— 完成（MVP 事件模型，见 `docs/targets.md`）。
4. KubeJS 生成器 —— 完成（MVP 事件/动作子集）。
5. Fabric 生成器 —— 注册已完成：生成工程在真实 26.2 依赖下编译通过
   （`tools/build_fabric.py out build` → `BUILD SUCCESSFUL`，产出可分发的 mod jar）。
   事件/动作保持门控，直到每条映射在同一个循环中被证实。
6. 测试 / 示例 / 文档 / CI —— 完成（golden + 错误契约 + 门禁真实编译测试、CI
   workflow、文档、`.gitignore`）。

## 验证哲学

每个阶段都带测试。Golden 测试锁定产出的精确字节。Fabric 那条「生成的 Java 在真实
依赖下可编译」由一条可选运行的集成测试来做真实 Gradle 编译证明；代码生成器只允许
发出**已证明能编译**的 API，未证明的一律被能力矩阵明确拒绝。