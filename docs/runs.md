# Runs and runtime context

A run is the durable record of an execution.

## Default layout

```text
.rlab/runs/<operation>_<name>_<timestamp>/
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

## Statuses

A run status is one of:

```text
created
planned
running
completed
failed
cancelled
stale
reproduced
```

The state machine is Rust-owned. Invalid transitions are rejected.

## Runtime context

Use context helpers inside user code:

```python
ctx.log_metric("loss", 0.2)
ctx.log_metrics({"loss": 0.2, "accuracy": 0.91})
path = ctx.output_path("model.pt")
path.write_bytes(b"...")
ctx.save_artifact(path, name="checkpoint", kind="model")
```

The Python context is Rust-backed. Rust validates events and writes durable files.

## Inspecting runs

```bash
rlab runs list
rlab runs show <run-id>
rlab errors <run-id>
rlab table <run-id>
```

`rlab runs show` includes the manifest, metric summary, result payload, logs,
error text, and registered artifact references.
