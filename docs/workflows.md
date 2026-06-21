# Workflows

A workflow composes multiple steps into one execution.

## Decorated workflow

```python
import rlab

lab = rlab.Project()

@lab.workflow("project.training_flow", steps=("prepare", "train"))
def training_flow(ctx):
    ctx.log_metric("prepared", 1.0)
    ctx.log_metric("loss", 0.2)
    return {"loss": 0.2}
```

Run:

```bash
rlab run workflow:project.training_flow
```

The `steps` metadata is descriptive. Python still exposes one callable:
`def training_flow(ctx)`. If the workflow needs child runs, call `ctx.run(...)` from
inside the workflow and rlab records the child job evidence.
