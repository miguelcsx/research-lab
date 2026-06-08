from __future__ import annotations

import typer

from rlab.artifacts.audit import AuditTrail
from rlab.artifacts.lineage import ArtifactLineageGraph
from rlab.cli.state import CliState
from rlab.constants import RUNS_DB_NAME
from rlab.invalidation.service import InvalidationService
from rlab.runs.index import RunIndex


def command(
    ctx: typer.Context,
    subject: str,
    reason: str = typer.Option(..., "--reason", "-r"),
    by: str | None = typer.Option(None, "--by"),
) -> None:
    """Mark an artifact or run as invalid and propagate staleness."""
    state: CliState = ctx.obj

    lineage = ArtifactLineageGraph(state.root / ".rlab" / "lineage.db")
    run_index = RunIndex(state.root / ".rlab" / RUNS_DB_NAME)
    audit = AuditTrail(state.root / ".rlab" / "audit.jsonl")

    service = InvalidationService(lineage, run_index, audit)
    record = service.invalidate(subject, reason, invalidated_by=by, runs_dir=state.root / "runs")

    state.console.print(f"[red]Invalidated:[/red] {subject}")
    state.console.print(f"Reason: {reason}")
    if record.affected:
        state.console.print(
            f"\n[yellow]{len(record.affected)} downstream item(s) marked stale:[/yellow]"
        )
        for item in record.affected:
            state.console.print(f"  {item}")
