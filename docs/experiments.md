# Experiments

An experiment is a named research execution unit.

## Minimal experiment

```python
import rlab

lab = rlab.Project()

@lab.experiment("sweep")
def sweep(ctx):
    ctx.log_metric("loss", 0.2)
    return {"ok": True}
```

Run it:

```bash
rlab run experiment:sweep
```

## Metadata

```python
@lab.experiment(
    "learning_rate_sweep",
    question="How does learning rate affect validation loss?",
    hypothesis="Lower learning rates improve stability.",
    matrix={"lr": [1e-3, 3e-4, 1e-4], "batch_size": [16, 32]},
    metrics=("val_loss", "runtime_seconds"),
    seeds=(0, 1, 2),
)
def learning_rate_sweep(ctx):
    loss = train(
        lr=ctx.params["lr"],
        batch_size=ctx.params["batch_size"],
        seed=ctx.seed,
    )
    ctx.log_metric("val_loss", loss)
    return {"loss": loss}
```

`rlab run` creates one durable run for every `matrix × seeds` job. The selected
seed is available as `ctx.seed`; explicit `--param` values are merged into every
job and take precedence over matrix values.

## Matrix helpers

```python
from rlab import grid, choice, uniform, log_uniform, Sample

matrix = grid({
    "optimizer": ["adam", "sgd"],
    "lr": [1e-3, 1e-4],
}).where(lambda row: not (row["optimizer"] == "sgd" and row["lr"] < 1e-4))

sample = Sample({
    "lr": log_uniform(1e-5, 1e-3),
    "dropout": choice([0.0, 0.1, 0.2]),
}, n=20, seed=42)
```

## Return values

An experiment may return:

- `None`;
- `dict`;
- `ResultBundle`.

Metrics should be logged through `ctx.log_metric` or returned in a `ResultBundle`.
