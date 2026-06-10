# Core concepts

`rlab` has four core concepts: project, registry, runtime, and run.

## Project

A project is a directory where research code lives. It may contain `lab.toml`, but that file is optional for basic usage.

Project root discovery uses this order:

1. explicit `--root`;
2. nearest `lab.toml`;
3. nearest `pyproject.toml`;
4. nearest `.git` directory;
5. current working directory.

In Python, the project object is the user's declaration surface:

```python
import rlab

lab = rlab.Project()
```

A project owns a registry of declarations.

## Registry

The registry is the in-memory catalog of declarations discovered by importing project modules.

Examples of registry records:

- experiment;
- workflow;
- component;
- benchmark;
- evaluation;
- source;
- transform;
- dataset;
- adapter.

Durable registry records are declarative and reproducible. They store module, qualname, source, kind, name, version, tags, description, and metadata. They do not store process-local Python callable IDs.

## Runtime context

`RuntimeContext` is passed into user code. It exposes helpers such as:

```python
ctx.log_metric("loss", 0.2)
ctx.log_metrics({"loss": 0.2, "accuracy": 0.91})
ctx.note("training converged")
ctx.save_artifact("checkpoint", "outputs/model.pt")
ctx.save_table("summary", [{"metric": "loss", "value": 0.2}])
```

Python user code emits structured events. Rust validates and persists them.

## Run

A run is a durable execution record. Runs are written under `.rlab/runs` by default.

A run records:

- manifest;
- status;
- parameters;
- metrics;
- results;
- logs;
- notes;
- artifacts;
- reproducibility metadata.

The run state machine is Rust-owned. Python code cannot directly finalize a run.
