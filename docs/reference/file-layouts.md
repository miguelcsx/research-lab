# Generated file layouts

This document describes files written by `rlab`.

## Run directory

```text
runs/<operation>_<name>_<timestamp>/
├── run.yaml
├── status.txt
├── params.json
├── metrics.jsonl
├── metrics_summary.json
├── results.json
├── report.md
├── notes.jsonl
├── logs/
│   └── error.txt
├── tables/
├── figures/
├── artifacts/
├── results/
├── external/
└── reproducibility/
    ├── command.txt
    ├── git.json
    ├── git.diff
    ├── env.json
    ├── lockfile
    ├── pyproject.toml
    ├── uv.lock
    └── lab.toml
```

## `run.yaml`

Example:

```yaml
kind: run
name: experiment_sweep_1700000000000
version: '1'
operation: experiment
status: completed
created_at: '2026-01-01T00:00:00+00:00'
updated_at: '2026-01-01T00:01:00+00:00'
command: []
parameters:
  path: experiments/sweep.py
tags:
  - paper
notes: initial sweep
error: null
parent_run: null
```

## `metrics.jsonl`

Each line is an independent metric event:

```json
{"name":"accuracy","value":0.91,"timestamp":"2026-01-01T00:00:01+00:00","unit":"percentage"}
{"name":"loss","value":0.2,"timestamp":"2026-01-01T00:00:02+00:00"}
```

## `metrics_summary.json`

Latest value per metric:

```json
{
  "accuracy": 0.91,
  "loss": 0.2
}
```

## `params.json`

Parameters recorded for a run:

```json
{
  "lr": 0.001,
  "batch_size": 32
}
```

## `results.json`

Final structured result. For experiments it commonly contains:

```json
{
  "name": "sweep",
  "steps": [
    {
      "job_id": "0000",
      "params": {"lr": 0.001},
      "metrics": {"loss": 0.2},
      "artifacts": {},
      "error": null,
      "failure_kind": "unknown"
    }
  ]
}
```

## Dataset build artifact layout

```text
runs/data.build_project.clean_<timestamp>/
└── artifacts/
    └── dataset/
        ├── data.jsonl
        ├── data_report.md
        └── manifest.yaml
```

## Artifact store

```text
artifacts/
├── .index.sqlite3
├── objects/
│   └── <sha-prefix>/<sha-rest>
├── <artifact-kind>/
│   └── <name>@<version>.yaml
└── <artifact-kind>/
    └── <name>/
        └── <alias>
```

## Cache and local metadata

```text
.rlab/
├── runs.db
├── search.db
├── graph.db
├── lineage.db
├── audit.jsonl
├── decisions.jsonl
├── negatives.jsonl
├── ideas.jsonl
├── baselines.db
└── jobs.sqlite3
```

`runs/` is the canonical execution record. `.rlab/` is operational metadata and can often be rebuilt, except for journal files you intentionally preserve.
