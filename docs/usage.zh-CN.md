# pymod CLI 参考与错误码（中文）

```
pymod check <文件> [--target/-t datapack|kubejs|fabric]
pymod generate <文件> --target/-t <目标> --out/-o <目录> [--game <版本>] [--pack-format <整数>]
pymod --version | --help
```

## check

把 DSL 文件解析并降级为 IR；带 `--target` 时再按该目标的能力矩阵校验。一次性打印所有问题，带 `文件:行:列` 与稳定错误码。

- 退出码 `0` —— 通过
- 退出码 `1` —— 解析/降级错误，或（带上 `--target` 时）校验失败

在 CI 里跑 `pymod check file -t <目标>`，可以让产物永远可分发。

## generate

先跑 `check --target`（有问题则打印报告并以 `1` 退出），再把目标写进 `--out`：

| 目标 | 产物 |
|---|---|
| datapack | `pack.mcmeta`、`data/<modid>/{tags,advancement,function}/...`、`mod_manifest.json` |
| kubejs | `server_scripts/<modid>.js` |
| fabric | 标准 Fabric Loom 工程（`gradle build` / `python tools/build_fabric.py out build` 编译） |

`--game` 选择游戏版本档案（默认读 `gameprofiles.json`）。`--pack-format` 覆盖数据包格式号。

## 错误码（部分、稳定子集）

前端（抛异常）：`syntax-error`、`unsupported-import`、`unsupported-statement`、
`unsupported-call`、`unsupported-expression`、`unsupported-literal`、
`unsupported-condition`、`missing-header`、`bad-modid`、`unknown-header-key`、
`header-args`、`handler-*`、`register-*`、`unknown-name`。

IR 降级：`missing-header`、`unknown-register-kind`、`duplicate-registration`、
`unknown-prop`、`unknown-event`、`unknown-action`、`bad-action-args`、
`bad-condition`、`unknown-param`、`bad-type`。

目标校验（收集式、落在 Report 里）：`target-unsupported-registration`、
`target-unsupported-event`、`target-unsupported-action`、`capability-note`，
以及生成器级 `target-not-implemented`、`datapack-unsupported-guard`、
`kubejs-unsupported-guard`、`bad-tag-category`。

错误码的用途：测试与工具可以直接断言**哪一条保证被破坏了**，而不必匹配脆弱的错误文案。