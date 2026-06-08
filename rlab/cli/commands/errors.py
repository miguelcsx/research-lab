from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.errors_analysis.compare import compare_runs_errors

app = typer.Typer(help="Failure analysis: regressions, improvements, and error categories.")


@app.command("compare")
def compare(
    ctx: typer.Context,
    baseline: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    candidate: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    metric: Annotated[str, typer.Option("--metric")],
    by: Annotated[str, typer.Option("--by")] = "category",
) -> None:
    """Compare per-example or per-category metric values between two runs."""
    state: CliState = ctx.obj
    result = compare_runs_errors(baseline, candidate, metric=metric, by=by)
    if result.regressions:
        state.console.print(f"[red]Regressions ({len(result.regressions)}):[/red]")
        state.console.print(
            table(
                "Regressions",
                [
                    {
                        "category": r.category,
                        "delta": r.delta,
                        "baseline": r.baseline,
                        "candidate": r.candidate,
                    }
                    for r in result.regressions
                ],
            )
        )
    if result.improvements:
        state.console.print(f"[green]Improvements ({len(result.improvements)}):[/green]")
        state.console.print(
            table(
                "Improvements",
                [
                    {
                        "category": r.category,
                        "delta": r.delta,
                        "baseline": r.baseline,
                        "candidate": r.candidate,
                    }
                    for r in result.improvements
                ],
            )
        )
    if not result.regressions and not result.improvements:
        state.console.print("[dim]No changes detected.[/dim]")
