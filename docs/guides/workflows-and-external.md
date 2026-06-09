# Workflows and external commands

Workflows compose multiple steps into one execution. Steps can be Python functions or external commands.

## Define a Python workflow

```python
import rlab

@rlab.workflow(
    "project.pipeline",
    step="prepare",
    description="Prepare data, train model, evaluate model.",
)
def prepare(ctx: rlab.WorkflowContext) -> None:
    ctx.note("Preparing inputs")
    ctx.log_metric("prepared", 1.0)


@rlab.workflow("project.pipeline", step="train")
def train(ctx: rlab.WorkflowContext) -> dict[str, float]:
    return {"loss": 0.2}
```

Functions with the same workflow name are composed in declaration order. A
step may return `None`, `dict[str, float]`, or `rlab.ResultBundle`.

Run it through an experiment:

```python
@rlab.experiment(
    "pipeline_sweep",
    question="Which preprocessing method works best?",
    matrix={"method": ["raw", "clean"]},
    workflow="project.pipeline",
)
def experiment(ctx: rlab.RuntimeContext) -> None:
    del ctx
```

## WorkflowContext

A workflow step receives:

```python
ctx.runtime
ctx.step_name
ctx.step_index
ctx.params
ctx.seed
```

Helpers:

```python
ctx.log_metric("loss", 0.3)
ctx.save_artifact("model.pt", "outputs/model.pt")
ctx.note("Step completed")
```

Metrics logged from `WorkflowContext` are also included in the step bundle.

## Inline workflow steps

You can build a workflow from objects:

```python
def train(ctx: rlab.WorkflowContext) -> dict[str, float]:
    return {"loss": 0.2}

workflow = rlab.define_workflow(
    "project.small",
    steps=(
        rlab.WorkflowStep(name="train", fn=train),
    )
)
```

This is useful in tests or small scripts.

## ExternalStep

Use `ExternalStep` when a step is a command-line program.

```python
workflow = rlab.define_workflow(
    "project.external",
    steps=(
        rlab.ExternalStep(
            name="compile",
            command=("make", "benchmark"),
            cwd="external/project",
            timeout_seconds=300,
        ),
    )
)
```

`rlab` captures stdout and stderr under:

```text
runs/<run-id>/external/<step-name>.stdout
runs/<run-id>/external/<step-name>.stderr
```

## External parsers

An external step can parse stdout into metrics.

```python
def parse(stdout: str) -> dict[str, float]:
    return {"score": float(stdout.strip())}

rlab.ExternalStep(
    name="score",
    command=("python", "score.py"),
    parser=parse,
)
```

You can also reference a parser as:

```text
module.path:function_name
```

```python
rlab.ExternalStep(
    name="score",
    command=("python", "score.py"),
    parser="project.parsers:parse_score",
)
```

## External command sandboxing

External runners use a restricted environment helper. By default, only common safe variables are preserved, such as:

```text
PATH
HOME
LANG
LC_ALL
TMPDIR
CUDA_VISIBLE_DEVICES
```

Explicit environment variables can be passed in `ExternalCommand.env` or `ExternalStep.env`.

## External repositories

The helper `checkout_repository(url, revision, cache_root)` clones and checks out a specific revision into cache. Use it when you must run official code at a fixed commit.

```python
from rlab.external.repo import checkout_repository

repo = checkout_repository(
    "https://github.com/org/official-eval.git",
    "abc123",
    runtime.paths.cache / "external",
)
```

When official scripts write to fixed directories inside the checkout, declare
where those directories should live in rlab artifact storage:

```python
@rlab.adapter("project.official")
class OfficialAdapter(rlab.BaseAdapter):
    def external_output_dirs(
        self, ctx: rlab.AdapterContext
    ) -> dict[str | Path, str | Path]:
        return {
            "external/official-eval/results": "official-eval/results",
        }

    def command(self, ctx: rlab.AdapterContext) -> rlab.ExternalCommand:
        return rlab.ExternalCommand(
            args=("bash", "scripts/evaluate.sh"),
            cwd=ctx.project_path("external/official-eval"),
        )
```

`BaseAdapter.prepare()` creates the artifact directory, migrates existing
files, and links the external tool's fixed output path to it. Use
`ctx.project_path(...)` and `ctx.artifact_path(...)` whenever adapter inputs
contain project-relative paths.

For version-controlled external repositories, keep the checkout immutable by
using a per-run workspace:

```python
workspace = ctx.external_workspace(
    "external/official-eval",
    outputs={
        "results": "official-eval/results",
        "models": "official-eval/models",
    },
)
```

The workspace copies the checkout into the adapter sandbox, seeds existing
output files into artifact storage once, and redirects all subsequent writes
there. Use paths below `workspace` as the command `cwd` and repository root.

## When to use workflows

Use workflows when an experiment job has ordered phases:

- compile -> run -> parse metrics;
- preprocess -> train -> evaluate;
- generate mesh -> solve PDE -> render plot;
- build proof project -> run proof benchmark -> summarize failures.

Use a benchmark when the operation is a single atomic measurement. Use an evaluation suite when the operation is a task-based model evaluation.
