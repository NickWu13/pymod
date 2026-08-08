# pymod CLI reference

```
pymod check <file> [--target/-t datapack|kubejs|fabric]
pymod generate <file> --target/-t <target> --out/-o <dir> [--game <vers>] [--pack-format <int>]
pymod --version | --help
```

## check

Parses + builds the DSL file into IR, then (with `--target`) validates it against
that target's capability matrix. Prints every problem at once with
`file:line:col` and a stable error code.

- exit `0` — clean
- exit `1` — parse/build error, or (with `--target`) reported issues

Run `pymod check file -t <target>` in CI to keep artifacts shippable.

## generate

Runs `check --target` first (aborts with `1` on issues, printing the report),
then emits the target into `--out`:

| target | emitted |
|---|---|
| datapack | `pack.mcmeta`, `data/<modid>/{tags,advancement,function}/...`, `mod_manifest.json` |
| kubejs | `server_scripts/<modid>.js` |
| fabric | standard Fabric Loom project (build with `gradle build` / `tools/build_fabric.py out build`) |

`--game` selects a game profile (default from `gameprofiles.json`). `--pack-format`
overrides the data-pack format number.

## Error codes (partial, stable subset)

Front end (exceptions): `syntax-error`, `unsupported-import`, `unsupported-statement`,
`unsupported-call`, `unsupported-expression`, `unsupported-literal`,
`unsupported-condition`, `missing-header`, `bad-modid`, `unknown-header-key`,
`header-args`, `handler-*`, `register-*`, `unknown-name`.

IR builder: `missing-header`, `unknown-register-kind`, `duplicate-registration`,
`unknown-prop`, `unknown-event`, `unknown-action`, `bad-action-args`,
`bad-condition`, `unknown-param`, `bad-type`.

Checker (per-target, collected): `target-unsupported-registration`,
`target-unsupported-event`, `target-unsupported-action`, `capability-note`,
and generator-level `target-not-implemented`, `datapack-unsupported-guard`,
`kubejs-unsupported-guard`, `bad-tag-category`.

Purpose of the codes: tests and tooling can assert *which* guarantee broke
without brittle message matching.