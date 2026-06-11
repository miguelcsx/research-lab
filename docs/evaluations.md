# Evaluations

An evaluation suite measures a model/system across one or more tasks.

## Define a component and evaluation task

```python
import rlab

lab = rlab.Project()

@lab.component("model", "project.constant")
class ConstantModel:
    def predict(self, x):
        return 1

@lab.evaluation("project.quick", "score")
def score(model, ctx):
    value = float(model.predict("x") == 1)
    ctx.log_metric("score.score", value)
    return {"score": value}
```

Run:

```bash
rlab evaluate project.quick --model model:project.constant
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
