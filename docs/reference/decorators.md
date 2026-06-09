# Declaration reference

`rlab` declarations register typed project objects when their module is
imported. Decorators bind metadata to code that executes. Immutable definitions
without Python execution use direct functional declarations.

## `@rlab.component(kind, name)`

```python
@rlab.component("model", "project.small")
class SmallModel:
    ...
```

## `@rlab.benchmark(name, target=kind)`

```python
@rlab.benchmark("project.latency", target="model")
def latency(model: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    return {"latency_ms": 10.0}
```

## `@rlab.evaluation(suite, task)`

Tasks sharing a suite name are composed in declaration order.

```python
@rlab.evaluation("project.quick", "accuracy")
def accuracy(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"accuracy": evaluate(model, ctx)}
```

## `@rlab.experiment(name, question=..., ...)`

The decorated function is the per-job execution function. The decorator stores
the immutable `Experiment` definition directly, so no provider function is
needed.

```python
@rlab.experiment(
    "sweep",
    question="Which learning rate is best?",
    matrix={"lr": [1e-3, 1e-4]},
    metrics=("loss",),
)
def sweep(ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"loss": train(lr=float(ctx.params["lr"]))}
```

## `@rlab.workflow(name, step=...)`

Steps sharing a workflow name are composed in declaration order.

```python
@rlab.workflow("project.pipeline", step="prepare")
def prepare(ctx: rlab.WorkflowContext) -> None:
    ctx.note("prepared")


@rlab.workflow("project.pipeline", step="train")
def train(ctx: rlab.WorkflowContext) -> dict[str, float]:
    return {"loss": 0.1}
```

Use `rlab.define_workflow(...)` for explicit or external steps:

```python
rlab.define_workflow(
    "project.external",
    steps=(
        rlab.ExternalStep(name="build", command=("make",)),
        rlab.ExternalStep(name="run", command=("./benchmark",)),
    ),
)
```

## `@rlab.study(name, question=..., ...)`

Attach a study plan to an experiment declaration:

```python
@rlab.study(
    "project.optimizers",
    question="Which optimizer generalizes best?",
    experiments=("optimizer_sweep",),
    outcomes=("validation_loss",),
)
@rlab.experiment(
    "optimizer_sweep",
    question="How does optimizer choice affect validation loss?",
    matrix={"optimizer": ["adam", "sgd"]},
)
def optimizer_sweep(ctx: rlab.RuntimeContext) -> dict[str, float]:
    return run_optimizer(ctx.params)
```

## Other decorators

- `@rlab.adapter(name)` registers an external adapter class.
- `rlab.external_evaluation(...)` registers immutable external command config.
- `@rlab.result_schema(name)` registers a result schema class.

## Dataset registration

Datasets compose typed `DatasetRecipe` objects and register one
`DatasetCatalog`. See [Data recipes](../guides/data-pipelines.md).

## Versions

Declaration versions use semantic versioning:

```python
@rlab.benchmark("project.latency", target="model", version="1.0.0")
def latency(model: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    ...
```
