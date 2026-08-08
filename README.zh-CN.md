# pymod — 中文文档

> 用受限的 Python DSL 描述 Minecraft Java 版 Mod / 数据包逻辑，自动校验并生成可运行的目标格式。

pymod 是一个**低代码 Mod 编译器，而不是 Python 运行时**：你的 `.py` 文件被解析、校验、
降级为标准化的中间表示（IR），再按目标的能力矩阵检查，最后生成成品。任何不支持的写法
都会**带文件与行号的明确报错**——绝不静默丢弃。

```
source(.py) → parser 白名单 → IR → checker 能力矩阵 → 生成器 → 成果物
```

目标优先级：**Data Pack（最稳） > KubeJS 脚本 > Fabric Java Mod（真实依赖编译验证）**。

## 中文文档

| 文档 | 内容 |
|---|---|
| [DSL 语法参考](docs/dsl.zh-CN.md) | `.py` DSL 的完整语法、事件/动作表、MVP 不支持清单 |
| [目标与能力矩阵](docs/targets.zh-CN.md) | datapack / kubejs / fabric 各自能表达什么、如何报错 |
| [CLI 参考与错误码](docs/usage.zh-CN.md) | 命令、退出码、稳定错误码目录 |
| [设计与阶段日志](docs/01-plan.zh-CN.md) | 「混淆后时代」的 26.2 技术事实、六阶段记录、验证哲学 |

## 快速开始

```bash
pip install -e ".[test]"

pymod check examples/chaos.py                  # 语法/语义校验
pymod check examples/chaos.py --target datapack # 校验目标支持

pymod generate examples/chaos.py       --target datapack --out out/datapack
pymod generate examples/kubejs_demo.py --target kubejs  --out out/kubejs
pymod generate examples/fabric_demo.py --target fabric  --out out/fabric  # 产物用 gradle build 编译
```

## 目标

| 目标 | 产物 |
|---|---|
| datapack | `pack.mcmeta` + `data/<modid>/{tags,advancement,function}/...` |
| kubejs | `server_scripts/<modid>.js` |
| fabric | 标准 Fabric Loom 工程（真实 26.2 依赖下已编译验证） |

固定版本 **MC 26.2**（数据包格式 **107**，资源 **88**，均取自 Mojang 官方产物核验）。

## 测试与开发

```bash
python -m pytest tests/ -q                 # 快测套件（36 通过 + 1 门禁跳过）
PYMOD_RUN_FABRIC_BUILD=1 pytest -q tests/test_fabric_build.py   # 真实 Gradle 编译验证（慢，~3 分钟）
```

## 现状与已知限制（如实说明）

- **已完成**：阶段 0–6——`check` + datapack/kubejs/fabric 三目标生成；Fabric 工程已在真实 26.2 依赖下编译成功（产出可分发 mod jar）。
- **尚未做**：
  - Fabric 的**事件/动作仍被门控**——需逐项以「javap 读真实 API → 生成 → 真实编译通过」解锁，当前明确报 `target-unsupported-*`。
  - **游戏内行为未验证**：本机无 Minecraft 实例，datapack/fabric 产物只做了编译与结构验证，未做进服/进游戏的实测。

## 目录结构

```
src/pymod/
├── cli.py                 # check / generate 子命令
├── errors.py              # SourceLoc + PyModError + Issue
├── gameprofiles.json      # ★ 所有版本敏感数字（单点真相）
├── dsl/parser.py          # ast 白名单前端
├── ir/                    # irnodes / builder / capability   IR 与能力矩阵
├── check/checker.py       # 目标能力校验（Report）
├── registry/gameprofile.py# 版本档案
├── report/                # Issue/Report 渲染
└── target/                # datapack / kubejs / fabric 生成器
tests/                     # 36 快测 + 1 门禁
examples/                  # 4 个 DSL 示例
tools/build_fabric.py      # 真实 Gradle 编译验证
docs/*.zh-CN.md            # 中文文档（本目录）
```