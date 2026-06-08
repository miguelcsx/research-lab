# Runs and results

Every meaningful operation in `rlab` writes a run directory. This is the primary unit of evidence.

## Create a run

```bash
rlab run experiments/exp.py
rlab bench tokenizer:project.byte project.tokenizer.length
rlab eval project.quick --model model:project.constant
rlab data build dataset:project.tiny
```

## Inspect runs

```bash
rlab runs list
rlab runs list --status completed
rlab runs show <run-id>
rlab runs logs <run-id>
rlab runs query "status = 'completed'"
rlab runs tail <run-id>
```

## Record metrics from Python

Inside an active runtime:

```python
ctx.log_metric("accuracy", 0.91, unit="percentage")
ctx.log_metric("latency_ms", 12.4, unit="ms")
```

Inside a workflow step:

```python
def step(ctx: rlab.WorkflowContext) -> None:
    ctx.log_metric("loss", 0.3)
```

## ResultBundle

`ResultBundle` is the standard typed container for outputs:

```python
return rlab.ResultBundle(
    metrics=(
        rlab.Metric(name="accuracy", value=0.91, unit="percentage"),
        rlab.Metric(name="loss", value=0.2),
    ),
    figures=(
        rlab.FigureArtifact(name="loss_curve", path=Path("loss.png")),
    ),
    tables=(
        rlab.TableArtifact(name="summary", path=Path("summary.csv")),
    ),
)
```

A simpler helper exists:

```python
return rlab.bundle_from_metrics({"accuracy": 0.91, "loss": 0.2})
```

## Metric names

Use stable dotted metric names:

```text
accuracy
loss
latency.ms
throughput.tokens_per_second
eval.mmlu.accuracy
data.duplicate_rate
solver.l2_error
```

Avoid ambiguous names like `score`, `metric`, `result`, or `value` unless they are local to a small prototype.

## Units and directions

`Metric` includes:

```python
rlab.Metric(
    name="runtime",
    value=3.2,
    unit="s",
    direction=rlab.Direction.MINIMIZE,
)
```

The units registry knows common units like seconds, milliseconds, bytes, MiB, GiB, tokens/s, Joules, and dimensionless.

## Save tables

```python
ctx.save_table(
    "summary",
    [
        {"model": "small", "accuracy": 0.91},
        {"model": "large", "accuracy": 0.94},
    ],
)
```

This writes under `tables/`.

## Save figures

```python
fig = make_matplotlib_figure()
ctx.save_figure("loss_curve", fig, formats=("png", "pdf"))
```

This writes under `figures/loss_curve/`.

## Save artifacts

```python
ctx.save_artifact("checkpoint.pt", "outputs/checkpoint.pt")
```

This copies the file into the run-local `artifacts/` directory.

## Add notes

```python
ctx.note("Run converged after epoch 7.")
```

CLI:

```bash
rlab notes add <run-id> "The baseline failed on long sequences."
rlab notes list <run-id>
```

## Compare runs

```bash
rlab compare runs/
rlab compare runs/ --metric accuracy
rlab compare runs/ --format csv --output reports/comparison.csv
```

## Diff runs

```bash
rlab diff runs/run_a runs/run_b
```

`diff` compares parameters, metrics, and recorded Git commits.

## Clean failed runs

```bash
rlab runs clean --failed --dry-run
rlab runs clean --failed
```

Do not delete runs used in papers, reports, decisions, or artifact lineage.
