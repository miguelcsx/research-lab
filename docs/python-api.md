# Python API

The Python API is intentionally thin: decorators register runtime entries, and
user callables receive a Rust-backed `RuntimeContext`.

```python
import rlab

lab = rlab.Project()
```

## Decorators

Runtime targets:

```python
@lab.experiment("train", params=TrainParams)
def train(ctx):
    params = ctx.params(TrainParams)
    ...

@lab.study("sweep", targets=("experiment:train",), params={"steps": 1000})
def sweep(ctx):
    return None

@lab.workflow("train_eval", steps=({"target": "experiment:train"},))
def train_eval(ctx):
    ...

@lab.benchmark("quality", target="model:*")
def quality(ctx):
    ...

@lab.evaluation("blimp", adapter="adapter:babylm_eval")
def blimp(ctx):
    ...
```

Support entries:

```python
@lab.loader("artifact")
def artifact_loader(ctx):
    ...

@lab.adapter("external_tool")
def external_tool(ctx):
    ...
```

Support decorators are `adapter`, `loader`, `executor`, `resolver`, `exporter`,
`reporter`, and `notifier`. They are discoverable support entries, not direct
`rlab run` targets.

## Runtime Context

All runtime callables use one signature:

```python
def target(ctx):
    ...
```

Common helpers:

```python
params = ctx.params(MyParams)
raw = ctx.params_dict()
target = ctx.param("target")
ctx.log_metric("loss", 0.2)
path = ctx.output_path("model.pt")
ctx.save_artifact(path, name="checkpoint", kind="model")
child = ctx.run("experiment:child", {"seed": 1})
```

Run external tools through the runtime:

```python
result = ctx.run_external(
    "tool",
    rlab.ExternalCommand(args=("python", "tool.py"), cwd=ctx.project_root),
)
```

## Results

Return JSON-compatible data or a `ResultBundle`:

```python
@lab.experiment("simple")
def simple(ctx):
    ctx.log_metric("loss", 0.2)
    return {"ok": True}
```

## Non-Goals

`rlab` does not provide component builders, datasets, pipelines, filters, or
domain-specific declaration helpers. Define scientific objects as normal
project code and call them from runtime entries.
