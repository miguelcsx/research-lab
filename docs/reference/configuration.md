# Configuration reference

`rlab` configuration is loaded from:

1. `lab.toml`;
2. environment variables beginning with `RLAB__`;
3. CLI overrides passed as `--set key=value`.

Later sources override earlier sources.

## Environment variable overrides

Environment variables use `RLAB__` and double underscores for nesting.

```bash
export RLAB__PROJECT__NAME=my-project
export RLAB__PATHS__RUNS=custom-runs
```

This maps to:

```toml
[project]
name = "my-project"

[paths]
runs = "custom-runs"
```

## CLI overrides

Commands such as `rlab run` accept:

```bash
rlab run experiments/exp.py --set launcher.timeout_seconds=600
```

Values are parsed as JSON when possible:

```bash
--set reproducibility.capture_env=false
--set launcher.jobs=4
--set project.name='"quoted-name"'
```

## Full model

```toml
[project]
name = "research-project"
team = "team-name"
owner = "owner-name"

[modules]
load = ["components.models", "benchmarks.main"]

[paths]
runs = "runs"
artifacts = "artifacts"
manifests = ["manifests"]
reports = "reports"
cache = ".rlab"

[tracking]
backend = "local"

[artifacts]
backend = "local"

[reproducibility]
capture_git = true
capture_diff = true
capture_env = true
capture_packages = true
capture_lockfile = true
capture_command = true
capture_data_manifests = true
allow_dirty = false
env_allowlist = []

[launcher]
default = "local"
jobs = 1
timeout_seconds = 3600
docker_image = "python:3.11"
```

## Path resolution

Relative paths are resolved relative to the project root.

```toml
[paths]
runs = "runs"
```

becomes:

```text
<project-root>/runs
```

Absolute paths remain absolute.

## Variable resolution

String values may use:

```text
${project.root}
```

Example:

```toml
[paths]
runs = "${project.root}/outputs/runs"
```

Environment variables may also be resolved by name.

## Tracking backend

Core backends:

```text
local
null
```

`local` writes run metadata to SQLite and run directories. `null` ignores tracking calls.

Other backend names require an installed adapter.

## Artifacts backend

Core backend:

```text
local
```

Other backend names require an installed adapter.

## Reproducibility fields

| Field | Default | Meaning |
|---|---:|---|
| `capture_git` | `true` | Capture commit, branch, remote, dirty state |
| `capture_diff` | `true` | Capture Git diff |
| `capture_env` | `true` | Capture Python/platform/env info |
| `capture_packages` | `true` | Capture installed packages |
| `capture_lockfile` | `true` | Copy lockfiles/project files |
| `capture_command` | `true` | Write command text |
| `capture_data_manifests` | `true` | Capture input dataset manifests |
| `allow_dirty` | `false` | Allow dirty Git state by policy |
| `env_allowlist` | `[]` | Env vars allowed to be preserved despite sensitivity |

## Validate config

```bash
rlab config validate
rlab config show
rlab config paths
```
