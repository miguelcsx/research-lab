from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.stats.compare import compare_runs

app = typer.Typer(help="Statistical testing and uncertainty quantification.")


@app.command("compare")
def compare(
    ctx: typer.Context,
    baseline: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    candidate: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    metric: Annotated[str, typer.Option("--metric")],
    method: Annotated[str, typer.Option("--method")] = "bootstrap",
    confidence: Annotated[float, typer.Option("--confidence")] = 0.95,
    repetitions: Annotated[int, typer.Option("--repetitions")] = 1000,
) -> None:
    """Compare a metric between two runs with confidence intervals."""
    state: CliState = ctx.obj
    result = compare_runs(
        baseline,
        candidate,
        metric,
        method=method,
        confidence=confidence,
        repetitions=repetitions,
    )
    rows = [
        {
            "metric": result.metric,
            "baseline": result.baseline,
            "candidate": result.candidate,
            "delta": result.delta,
            "ci_lower": result.ci_lower,
            "ci_upper": result.ci_upper,
            "reliable": result.reliable,
            "method": result.method,
        }
    ]
    state.console.print(table("Comparison", rows))
