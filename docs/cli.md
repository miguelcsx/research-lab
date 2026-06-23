# CLI reference

The primary command is `rlab`.

```bash
rlab <command> [options]
python -m rlab <command> [options]
```

`python -m rlab` is a fallback shim into the same Rust-owned command implementation.

Every command supports stable machine-readable output with `--json`.

## Global options

```text
--root <path>     Project root. Defaults to automatic discovery.
--json            Emit stable JSON output.
--strict          Enable strict production checks where supported.
```

## Pure Rust commands

These commands do not need to start the Python runner:

```bash
rlab init
rlab validate
rlab doctor
rlab config show
rlab runs list
rlab runs show <run-id>
rlab artifact promote <path> --as <kind>:<name> --version <version>
rlab artifact describe artifact:<kind>/<name>@<version-or-alias>
rlab compare <runs-dir>
rlab migrate status
rlab migrate plan
rlab freeze run <run-id> --as <label>
rlab freeze lock <run-id>
```

## Python-hosted commands orchestrated by Rust

These commands may start `python -m rlab._runner` because they need to import project modules or execute Python callables:

```bash
rlab discover
rlab run experiment:<name>
rlab run workflow:<name>
rlab run benchmark:<name>
rlab run evaluation:<name>
rlab study run <name>
```

Rust still owns request validation, run state, persistence, and final output.

## Initialization

```bash
rlab init
rlab init project <name>
rlab init experiment <name>
rlab init benchmark <name>
rlab init workflow <name>
rlab init adapter <name>
```

`rlab init` writes a minimal `lab.toml` and conventional folders. It is optional for zero-config projects.

## Discovery

```bash
rlab discover
rlab discover experiment
rlab discover support
rlab discover --all
rlab discover --refresh
rlab discover --no-cache
rlab discover --strict
```

Discovery imports configured modules and returns runtime catalog records. Default
discovery shows runnable and support entries; `--all` also shows internal/custom
entries.

## Running experiments

```bash
rlab run experiment:sweep
rlab run experiment:sweep --json
rlab run experiment:sweep --strict
rlab run experiment:sweep --param lr=0.001 --param batch_size=32
```

## Runs

```bash
rlab runs list
rlab runs list --json
rlab runs show <run-id>
rlab runs show <run-id> --json
```

`runs show` includes metrics, results, logs, errors, and artifact references.

## Artifacts

```bash
rlab artifact promote outputs/model.pt --as model:small --version 1 --alias candidate
rlab artifact describe artifact:model/small@1
rlab artifact describe artifact:model/small@candidate
```

## Reports and handoff

```bash
rlab report run <run-id> --output reports/run.md
rlab report compare .rlab/runs --output reports/comparison.md
rlab view report @workflow:report.model_comparison/outputs/reports/model_comparison
rlab open figure @workflow:report.model_comparison/outputs/reports/model_comparison/figures/model_comparison.png
rlab handoff <run-id> --to team-b
```

## Journals and notes

```bash
rlab notes add <run-id> "Training diverged after epoch 3."
rlab notes list <run-id>

rlab journal decision add "Use model v3 for the paper" --run <run-id>
rlab journal decision list
rlab journal negative add "hypothesis" "what was tried" "why it failed"
rlab journal ideas add "Try source-balanced data mixing"
```

## Search and graph

```bash
rlab search "dedup"
rlab graph lineage run:<run-id>
rlab impact artifact:model/small@candidate
rlab invalidate artifact:model/small@candidate --reason "bad calibration"
```

## CI helpers

```bash
rlab ci smoke
rlab ci compare --baseline <run-id> --candidate <run-id> --metric accuracy --threshold 0.01
rlab ci reproducibility-check
```

## Planning and stats

```bash
rlab plan power --effect-size 0.5 --variance 1.0 --alpha 0.05 --power 0.8
rlab plan cost experiment:sweep --seconds-per-job 60 --storage-gb-per-job 0.2
rlab stats compare --a 0.1,0.2,0.3 --b 0.2,0.3,0.4
```
