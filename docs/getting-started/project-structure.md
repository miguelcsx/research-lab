# Project structure

An `rlab` project is any directory with a `lab.toml` file. Most commands receive a `--root` option; by default the root is the current working directory.

## Minimal project

```text
project/
├── lab.toml
├── pyproject.toml
├── experiments/
├── components/
├── benchmarks/
├── manifests/
├── runs/
├── artifacts/
└── reports/
```

Only `lab.toml` is required for `rlab` to treat a directory as a project, but the standard folders make projects easier to understand.

## `lab.toml`

`lab.toml` defines project metadata, module loading, output paths, tracking behavior, artifact behavior, reproducibility capture, and launcher defaults.

Example:

```toml
[project]
name = "my-research"
team = "compiler-lab"
owner = "miguel"

[modules]
load = [
  "components.models",
  "benchmarks.performance",
  "experiments.main",
]

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
allow_dirty = false

[launcher]
default = "local"
jobs = 1
timeout_seconds = 3600
docker_image = "python:3.11"
```

## Source folders

`rlab` does not require a specific source layout. The generated templates use conventional folders:

| Folder | Purpose |
|---|---|
| `components/` | Reusable classes/functions registered with `@rlab.component` |
| `benchmarks/` | Atomic measurements registered with `@rlab.benchmark` |
| `evaluations/` | Tasks composed with `@rlab.evaluation` or external suites |
| `ingest/` | Data sources, transforms, checks, metrics, and dataset variants |
| `workflows/` | Steps composed with `@rlab.workflow` |
| `experiments/` | Experiment definitions registered with `@rlab.experiment` |
| `adapters/` | Adapters that invoke external repositories or tools |
| `manifests/` | Dataset manifests and other explicit input manifests |
| `tests/` | Project-specific tests |

## Runtime folders

`rlab` writes runtime state to these folders:

| Folder | Written by | Meaning |
|---|---|---|
| `runs/` | experiments, benchmarks, evaluations, data builds | Full run records |
| `artifacts/` | artifact store | Promoted reusable outputs |
| `reports/` | report commands | Generated comparisons and reports |
| `.rlab/` | indexes, cache, jobs, journals | Local metadata and SQLite indexes |

The `.rlab/` directory is disposable cache and operational metadata. A run directory under `runs/` is the canonical evidence record.

## Project root discovery

The function `rlab.context.project.find_project()` walks upward until it finds `lab.toml`. The CLI instead accepts `--root`, defaulting to the current working directory.

```bash
rlab --root /path/to/project doctor
```

## Recommended `.gitignore`

```gitignore
.venv/
.rlab/
runs/
artifacts/
reports/*.zip
```

Commit `lab.toml`, source files, manifests, and small reference data when possible. Do not commit large generated run outputs unless they are intentionally frozen for a paper or release.
