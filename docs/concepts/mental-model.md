# Mental model

`rlab` has four major concepts: project, registry, runtime, and run.

## Project

A project is a directory with a `lab.toml`. The project owns:

- configuration;
- Python modules to load;
- paths for runs, artifacts, reports, manifests, and cache;
- local policy files;
- generated results.

## Registry

The registry is an in-memory catalog of things your project declares. Decorators register objects during module import.

Examples:

```python
@rlab.component("model", "small")
class SmallModel:
    ...

@rlab.benchmark("latency", target="model")
def latency(model, ctx):
    ...

@rlab.experiment(
    "sweep",
    question="Which model is fastest?",
    matrix={"model": ["small", "large"]},
)
def sweep(ctx: rlab.RuntimeContext) -> dict[str, float]:
    return run_trial(ctx.params)
```

When `rlab` builds a runtime, it loads every module listed in `lab.toml` and fills the registry.

Data pipelines use the same model. Sources and stages are registered frozen
dataclasses, pipelines are ordered component references, and datasets bind one
source and pipeline to sinks, checks, metrics, and an audit policy. Runtime
execution resolves only explicit, semantically versioned registry entries.

## Runtime context

`RuntimeContext` is the object passed into execution paths. It contains:

- effective `LabConfig`;
- resolved `ProjectPaths`;
- active `Registry`;
- active `run_id` and `run_dir`, when inside a run;
- seed;
- parameter values;
- resource metadata.

It also provides helpers:

```python
ctx.log_metric("loss", 0.42)
ctx.note("training converged")
ctx.save_table("summary", [{"metric": "loss", "value": 0.42}])
ctx.save_figure("curve", fig)
ctx.save_artifact("checkpoint.pt", "outputs/checkpoint.pt")
```

## Run

A run is a durable execution record. Experiments, benchmarks, evaluations, and data builds all create runs. A run is not just a log file; it is a structured directory.

Typical run:

```text
runs/experiment_name_1700000000000/
├── run.yaml
├── status.txt
├── params.json
├── metrics.jsonl
├── metrics_summary.json
├── results.json
├── report.md
├── notes.jsonl
├── logs/
├── tables/
├── figures/
├── artifacts/
├── results/
└── reproducibility/
```

## Execution flow

The common flow is:

1. Load `lab.toml`.
2. Resolve project paths.
3. Create a new registry.
4. Import configured modules.
5. Execute a command.
6. Create a run session if the command produces a run.
7. Capture reproducibility metadata.
8. Execute user code.
9. Record metrics/results/artifacts.
10. Mark the run completed or failed.

## Determinism boundary

`rlab` does not decide research strategy. It provides deterministic primitives. A human, shell script, CI pipeline, or AI agent may decide what to call, but `rlab` only executes explicit commands and user-defined declarations.

## Why decorators?

Decorators solve a practical problem: research projects need discoverable named objects without a central imperative registry file. A decorator attaches metadata to normal Python code.

This:

```python
@rlab.benchmark("my.latency", target="model")
def latency(model, ctx):
    ...
```

means:

> When this module is imported under an active registry, register `latency` as a benchmark named `my.latency`, compatible with components whose target kind is `model`.
