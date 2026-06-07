from pathlib import Path

import typer

from rlab.cli.state import CliState
from rlab.reporting.compare import compare_runs
from rlab.reporting.export import export_rows

app = typer.Typer(help="Generate portable reports.")


@app.command("run")
def run_report(
    ctx: typer.Context,
    run: Path,
    output: Path = typer.Option(Path("reports/run.md")),
) -> None:
    state: CliState = ctx.obj
    export_rows(compare_runs((run,)), "md", state.root / output)
    state.console.print(state.root / output)


@app.command("compare")
def compare_report(
    ctx: typer.Context,
    runs: Path,
    output: Path = typer.Option(Path("reports/comparison.md")),
) -> None:
    state: CliState = ctx.obj
    paths = tuple(path for path in runs.iterdir() if (path / "run.yaml").exists())
    export_rows(compare_runs(paths), "md", state.root / output)
    state.console.print(state.root / output)
