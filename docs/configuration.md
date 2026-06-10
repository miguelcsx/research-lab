# Configuration

Configuration is layered. Later layers override earlier layers.

1. Built-in defaults.
2. `pyproject.toml` project metadata.
3. `[tool.rlab]` in `pyproject.toml`.
4. Optional `lab.toml`.
5. Environment variables beginning with `RLAB__`.
6. CLI `--set key=value` overrides.

## Built-in defaults

```toml
schema_version = 1

[paths]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
cache = ".rlab/cache"

[python]
modules = ["experiments"]
runner_module = "rlab._runner"

[production]
strict = false

[reproducibility]
capture_git = true
capture_diff = true
capture_env = true
require_clean_git = false
require_lockfile = false
```

## `pyproject.toml` integration

Use `[tool.rlab]` for lightweight configuration:

```toml
[tool.rlab]
modules = ["experiments", "benchmarks"]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
strict = false
```

## `lab.toml`

Use `lab.toml` for explicit research projects:

```toml
schema_version = 1

[project]
name = "my-research"
team = "compiler-lab"
owner = "alice"

[paths]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
cache = ".rlab/cache"

[python]
modules = ["experiments", "components", "benchmarks"]
runner_module = "rlab._runner"

[production]
strict = false

[reproducibility]
capture_git = true
capture_diff = true
capture_env = true
require_clean_git = false
require_lockfile = false
```

## Environment overrides

Nested keys use double underscores:

```bash
export RLAB__PRODUCTION__STRICT=true
export RLAB__PATHS__RUNS=.rlab/runs
```

## CLI overrides

```bash
rlab run experiment:sweep --set production.strict=true
```

## Inspect effective config

```bash
rlab config show
rlab config show --json
```
