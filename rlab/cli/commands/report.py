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
    narrative: bool = typer.Option(False, "--narrative", help="Render a full scientific narrative"),
) -> None:
    """Generate a markdown report for a single run."""
    state: CliState = ctx.obj
    if narrative:
        from rlab.reports.markdown import render_experiment_report

        text = render_experiment_report(run)
    else:
        from rlab.reports.markdown import render_run_report

        text = render_run_report(run)
    dest = state.root / output
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    state.console.print(dest)


@app.command("compare")
def compare_report(
    ctx: typer.Context,
    runs: Path,
    output: Path = typer.Option(Path("reports/comparison.md")),
) -> None:
    """Generate a comparison report across multiple runs."""
    state: CliState = ctx.obj
    paths = tuple(path for path in runs.iterdir() if (path / "run.yaml").exists())
    export_rows(compare_runs(paths), "md", state.root / output)
    state.console.print(state.root / output)
