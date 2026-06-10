# Workflows

A workflow composes multiple steps into one execution.

## Decorated workflow steps

```python
import rlab

lab = rlab.Project()

@lab.workflow("project.pipeline", step="prepare")
def prepare(ctx):
    ctx.note("Preparing inputs")
    ctx.log_metric("prepared", 1.0)

@lab.workflow("project.pipeline", step="train")
def train(ctx):
    ctx.log_metric("loss", 0.2)
    return {"loss": 0.2}
```

Run:

```bash
rlab run workflow:project.pipeline
```

Repeated declarations with the same workflow name are composed in declaration order.

## Imperative workflow definition

```python
workflow = lab.define_workflow(
    "project.small",
    steps=(
        rlab.WorkflowStep(name="train", fn=train),
    ),
)
```

## External steps

```python
workflow = lab.define_workflow(
    "project.external",
    steps=(
        rlab.ExternalStep(
            name="compile",
            command=("make", "benchmark"),
            cwd="external/project",
            timeout_seconds=300,
        ),
    ),
)
```

External step stdout/stderr are captured as run artifacts/logs.
