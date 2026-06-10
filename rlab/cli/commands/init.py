from typing import Annotated

import typer

from rlab.cli.state import CliState
from rlab.cli.templates import lock_project, write_project, write_skeleton

app = typer.Typer(help="Create projects and extension skeletons.")

_TEMPLATES = ["basic", "ai", "data", "simulation", "lean", "systems", "paper"]
_NEW_KINDS = [
    "experiment",
    "benchmark",
    "workflow",
    "ingest",
    "report",
    "adapter",
    "causal-experiment",
]


@app.command("project")
def project(
    ctx: typer.Context,
    name: str,
    template: Annotated[str, typer.Option("--template", "-t")] = "ai",
) -> None:
    """Create a new rlab project from a template."""
    if template not in _TEMPLATES:
        raise typer.BadParameter(
            f"Unknown template {template!r}; available: {', '.join(_TEMPLATES)}"
        )
    state: CliState = ctx.obj
    if (state.root / name).exists():
        raise typer.BadParameter(f"Project {name!r} already exists at {state.root / name}")
    generated = write_project(state.root, name, template=template)
    lock_project(generated)
    state.console.print(f"[green]Created project:[/green] {generated}")


@app.command("new")
def new(
    ctx: typer.Context,
    kind: Annotated[str, typer.Argument(help=f"One of: {', '.join(_NEW_KINDS)}")],
    name: str,
) -> None:
    """Generate a skeleton file for a benchmark, workflow, experiment, etc."""
    if kind not in _NEW_KINDS:
        raise typer.BadParameter(f"Unknown kind {kind!r}; available: {', '.join(_NEW_KINDS)}")
    state: CliState = ctx.obj
    project_module = state.root.name
    path = write_skeleton(state.root, kind, name, project_module=project_module)
    state.console.print(f"[green]Created:[/green] {path}")


@app.command("benchmark")
def benchmark(ctx: typer.Context, name: str) -> None:
    """Shortcut for `rlab init new benchmark <name>`."""
    new(ctx, "benchmark", name)


@app.command("experiment")
def experiment(ctx: typer.Context, name: str) -> None:
    """Shortcut for `rlab init new experiment <name>`."""
    new(ctx, "experiment", name)


@app.command("workflow")
def workflow(ctx: typer.Context, name: str) -> None:
    """Shortcut for `rlab init new workflow <name>`."""
    new(ctx, "workflow", name)


@app.command("adapter")
def adapter(ctx: typer.Context, name: str) -> None:
    """Shortcut for `rlab init new adapter <name>`."""
    new(ctx, "adapter", name)
