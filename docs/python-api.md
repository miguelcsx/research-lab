# Python API

The Python API is intentionally thin. It provides ergonomic declarations and user-code execution while delegating durable behavior to Rust.

## Import

```python
import rlab
```

## Project

```python
lab = rlab.Project()
```

`Project()` with no arguments resolves the current project from the effective config or working directory.

You may name a project explicitly:

```python
lab = rlab.Project("my-research")
```

## Decorators

All decorators are bound methods on `Project`.

There are no top-level decorators such as `@rlab.experiment`.

```python
@lab.experiment("sweep")
def sweep(ctx):
    return {"ok": True}
```

Supported decorator methods:

```python
lab.experiment(name, **metadata)
lab.experiment_from_spec(name, spec)
lab.study(name, **metadata)
lab.study_from_spec(name, spec)
lab.workflow(name, step="prepare")
lab.define_workflow(name, steps=(...))
lab.evaluation(suite, task)
lab.external_evaluation(name, **metadata)
lab.component(kind, name)
lab.benchmark(name, target="model")
lab.adapter(name)
lab.result_schema(name)
lab.source(name)
lab.transform(name)
lab.filter(name)
lab.group(name)
lab.dedup(name)
lab.sink(name)
lab.check(name)
lab.metric(name)
lab.pipeline(name, *stages, version="1", tags=(), description=None)
lab.dataset(name, source=..., pipeline=..., sinks=(), checks=(), metrics=(), audit=None)
```

## Runtime context

Experiment, workflow, benchmark, evaluation, and dataset code receives a context object.

Common methods:

```python
ctx.log_metric("loss", 0.2)
ctx.log_metrics({"loss": 0.2, "accuracy": 0.91})
ctx.note("important observation")
ctx.save_artifact("checkpoint", "outputs/model.pt")
ctx.save_table("summary", [{"metric": "loss", "value": 0.2}])
```

## Results

Return a dictionary for simple results:

```python
@lab.experiment("simple")
def simple(ctx):
    return {"ok": True, "loss": 0.2}
```

Or use result types:

```python
from rlab import Metric, ResultBundle

@lab.experiment("typed")
def typed(ctx):
    return ResultBundle(metrics=[Metric("loss", 0.2)])
```

## Data decisions

```python
return rlab.data_keep(record)
return rlab.data_update({**record, "text": text}, reason="stripped")
return rlab.data_drop("empty")
return rlab.data_boundary(value, kind="document")
```

## Public convenience helpers

```python
rlab.bundle_from_metrics({"loss": 0.2})
rlab.compare_runs(".rlab/runs", metric="loss")
rlab.compare_metric_arrays([1, 2, 3], [2, 3, 4])
rlab.estimate_required_repetitions(effect_size=0.5, variance=1.0, alpha=0.05, power=0.8)
rlab.estimate_budget(jobs=10, seconds_per_job=60, storage_gb_per_job=0.1)
```
