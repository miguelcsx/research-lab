# Experiments

An experiment is a declarative research plan. It describes a question, optional hypothesis, parameter matrix, execution method, expected outputs, and metadata.

## Minimal experiment

```python
import rlab

@rlab.experiment(
    "learning_rate_sweep",
    question="How does learning rate affect validation loss?",
    hypothesis="Lower learning rates improve stability but converge slower.",
    matrix={
        "lr": [1e-3, 3e-4, 1e-4],
        "batch_size": [16, 32],
    },
    metrics=("val_loss", "train_runtime_seconds"),
    decision_criteria="Choose the lowest loss within 10% of the fastest run.",
    seeds=(0, 1, 2),
)
def experiment(ctx: rlab.RuntimeContext) -> dict[str, float]:
    return train(ctx.params)
```

Run it:

```bash
rlab run experiments/learning_rate_sweep.py
```

## Fields

| Field | Purpose |
|---|---|
| `question` | Research question |
| `hypothesis` | Expected outcome |
| `decision_criteria` | How to decide from results |
| `assumptions` | Assumptions that must hold |
| `threats` | Threats to validity |
| `references` | Papers, issues, links, prior runs |
| `matrix` | Parameter grid, `Grid`, or `Sample` |
| `workflow` | Registered workflow to execute per job |
| `benchmarks` | Benchmarks to run when matrix contains `target` |
| `evaluations` | Evaluation suites to run when matrix contains `model` |
| `data` | Dataset reference or manifest reference |
| `metrics` | Expected metrics |
| `figures` | Expected figures |
| `tables` | Expected tables |
| `artifacts` | Expected artifacts |
| `seeds` | Repeated seeds |
| `resources` | Resource hints |
| `retry` | Retry policy |
| `after_run` | Post-run hooks, reserved for project conventions |

## Matrix expansion

Plain dictionary:

```python
matrix={
    "optimizer": ["adam", "sgd"],
    "lr": [1e-3, 1e-4],
}
```

This expands to four jobs.

Using `Grid`:

```python
from rlab import grid

matrix = grid({
    "solver": ["fdtd", "spectral"],
    "nx": [64, 128, 256],
}).where(lambda row: not (row["solver"] == "spectral" and row["nx"] == 64))
```

Using random sampling:

```python
from rlab import Sample, log_uniform, choice

matrix = Sample(
    {
        "lr": log_uniform(1e-5, 1e-3),
        "dropout": choice([0.0, 0.1, 0.2]),
    },
    n=20,
    seed=42,
)
```

## Dry run

Before executing:

```bash
rlab run experiments/sweep.py --dry-run
```

This prints the execution plan: job IDs, seeds, and parameter combinations.

## Running one job

```bash
rlab run experiments/sweep.py --only 0003
```

## Setting overrides

CLI overrides go through the config loader:

```bash
rlab run experiments/sweep.py --set launcher.timeout_seconds=600
```

## Seeds

If you set:

```python
seeds=(0, 1, 2)
matrix={"lr": [1e-3, 1e-4]}
```

`rlab` creates six jobs: every matrix row for every seed.

## Experiment execution modes

### Run function

The decorated experiment function executes once per matrix row and seed.

```python
@rlab.experiment(
    "train_sweep",
    question="Which learning rate minimizes validation loss?",
    matrix={"lr": [1e-3, 1e-4]},
)
def train(ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"val_loss": train_once(ctx.params)}
```

### Workflow

Use `workflow="name"` when each job executes a multi-step workflow.

```python
@rlab.experiment(
    "pipeline_sweep",
    question="Does preprocessing improve score?",
    matrix={"method": ["raw", "clean"]},
    workflow="project.pipeline",
)
def experiment(ctx: rlab.RuntimeContext) -> None:
    del ctx
```

### Benchmarks

If the matrix contains `target`, every declared benchmark runs against that target.

```python
@rlab.experiment(
    "tokenizer_length",
    question="Which tokenizer is shorter?",
    matrix={"target": ["tokenizer:a", "tokenizer:b"]},
    benchmarks=("project.token_count",),
)
def experiment(ctx: rlab.RuntimeContext) -> None:
    del ctx
```

### Evaluations

If the matrix contains `model`, every declared suite evaluates that model.

```python
@rlab.experiment(
    "model_quality",
    question="Which model performs best?",
    matrix={"model": ["model:small", "model:large"]},
    evaluations=("project.quick",),
)
def experiment(ctx: rlab.RuntimeContext) -> None:
    del ctx
```

## Resume

Resume skips successful jobs from a previous run:

```bash
rlab run experiments/sweep.py --resume runs/<previous-run-id> --name continued
```

## Retry policy

```python
from rlab.experiments.model import RetryPolicy
from rlab.constants import FailureKind

retry=RetryPolicy(
    max_attempts=3,
    on=(FailureKind.TIMEOUT, FailureKind.RESOURCE_ERROR),
    delay_seconds=10.0,
)
```

## Best practices

- Put the research question in `question`.
- Put expected outcomes in `hypothesis`.
- Record decision criteria before running.
- Use explicit metric names.
- Use `--dry-run` before expensive sweeps.
- Use multiple seeds when variance matters.
- Keep matrix values JSON-compatible.
- Save artifacts through `RuntimeContext` or `WorkflowContext`.
