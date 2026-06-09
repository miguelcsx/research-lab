# Decorators reference

Decorators register project objects into the active registry when a module is imported.

## `@rlab.component(kind, name)`

Registers a reusable component.

```python
@rlab.component("model", "project.small")
class SmallModel:
    ...
```

Reference:

```text
model:project.small
```

## `@rlab.benchmark(name, target=kind)`

Registers a benchmark for a component kind.

```python
@rlab.benchmark("project.latency", target="model")
def latency(model: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    return {"latency_ms": 10.0}
```

## `@rlab.suite(name)`

Registers an in-process evaluation suite.

```python
@rlab.suite("project.quick")
def quick() -> rlab.EvaluationSuite:
    return rlab.EvaluationSuite(tasks=(... ,))
```

## `@rlab.external_suite(name)`

Registers an external command evaluation suite.

```python
@rlab.external_suite("project.official")
def official() -> rlab.ExternalEvaluation:
    return rlab.ExternalEvaluation(...)
```

## `@rlab.experiment(name)`

Registers an experiment definition.

```python
@rlab.experiment("sweep")
def sweep() -> rlab.Experiment:
    return rlab.Experiment(question="...", matrix={...})
```

## `@rlab.workflow(name)`

Registers a workflow.

```python
@rlab.workflow("project.pipeline")
def pipeline() -> rlab.Workflow:
    return rlab.Workflow(steps=("project.step",))
```

## `@rlab.workflow_step(name)`

Registers a workflow step.

```python
@rlab.workflow_step("project.step")
def step(ctx: rlab.WorkflowContext) -> dict[str, float]:
    return {"score": 1.0}
```

## Dataset registration

Datasets do not use decorators. Compose typed `DatasetRecipe` objects and call
`rlab.register_datasets(rlab.DatasetCatalog(...))` once in the loaded module.
See [Data recipes](../guides/data-pipelines.md).

## `@rlab.baseline(name)`

Registers a baseline definition. The current CLI baseline store is SQLite-backed and can also be managed without decorators.

```python
@rlab.baseline("project.baseline")
def baseline():
    return ...
```

## `@rlab.result_schema(name)`

Registers a custom result schema.

```python
@rlab.result_schema("project.training")
class TrainingResult(rlab.ResultSchema):
    ...
```

## Signature expectations

Some registry kinds have minimum positional parameter counts:

| Kind | Expected parameters |
|---|---:|
| benchmark | 2: target, context |
| data source | 1: context |
| data transform | 2: records, context |
| data check | 2: records, context |
| data metric | 2: records, context |

## Version format

Decorator versions must be semantic versions:

```python
@rlab.benchmark("project.latency", target="model", version="1.0.0")
def latency(...):
    ...
```

Invalid:

```text
v1
1
latest
```
