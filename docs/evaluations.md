# Evaluations

An evaluation suite measures a model/system across one or more tasks.

## Define an Evaluation

```python
import rlab

lab = rlab.Project()

@lab.evaluation("project.quick")
def score(ctx):
    prediction = int(ctx.param("prediction", 1))
    value = float(prediction == 1)
    ctx.log_metric("score.score", value)
    return {"score": value}
```

Run:

```bash
rlab run evaluation:project.quick --set prediction=1
```

Successful evaluations print their metrics and an inspection command. A
nonzero external command exit fails the run.

## Metric naming

Evaluation task metrics should use:

```text
<task-name>.<metric-name>
```

Example:

```text
score.accuracy
score.loss
```

## Baselines

```bash
rlab baselines add gpt2_base --metric score.accuracy --value 0.82 --description "GPT-2 validation baseline"
rlab baselines list
rlab baselines compare <run-id>
```
