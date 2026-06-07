import typer

from rlab.cli.state import CliState
from rlab.cli.templates import lock_project, write_project

app = typer.Typer(help="Create projects and extension templates.")


@app.command("project")
def project(
    ctx: typer.Context,
    name: str,
) -> None:
    state: CliState = ctx.obj
    generated = write_project(state.root, name)
    lock_project(generated)
    state.console.print(generated)


@app.command("data-project")
def data_project(ctx: typer.Context, name: str) -> None:
    project(ctx, name)


def _template(ctx: typer.Context, kind: str, name: str) -> None:
    state: CliState = ctx.obj
    path = state.root / f"{name}.py"
    path.write_text(f"# {kind}: {name}\n")
    state.console.print(path)


@app.command("plugin")
def plugin(ctx: typer.Context, name: str) -> None:
    _template(ctx, "plugin", name)


@app.command("benchmark")
def benchmark(ctx: typer.Context, name: str) -> None:
    _template(ctx, "benchmark", name)


@app.command("experiment")
def experiment(ctx: typer.Context, name: str) -> None:
    _template(ctx, "experiment", name)


@app.command("suite")
def suite(ctx: typer.Context, name: str) -> None:
    _template(ctx, "suite", name)
