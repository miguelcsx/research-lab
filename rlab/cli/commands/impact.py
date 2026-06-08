from __future__ import annotations

import typer

from rlab.cli.state import CliState


def command(ctx: typer.Context, subject: str) -> None:
    """Show downstream impact of an artifact or dataset."""
    state: CliState = ctx.obj
    from rlab.artifacts.lineage import ArtifactLineageGraph

    lineage = ArtifactLineageGraph(state.root / ".rlab" / "lineage.db")
    descendants = lineage.descendants(subject)
    ancestors = lineage.ancestors(subject)
    if not descendants and not ancestors:
        state.console.print(f"[dim]No lineage found for {subject!r}.[/dim]")
        return
    state.console.print(f"\n[bold]Impact of:[/bold] {subject}")
    if ancestors:
        state.console.print("\n[bold]Produced from:[/bold]")
        for anc in ancestors:
            state.console.print(f"  {anc}")
    if descendants:
        state.console.print("\n[bold]Downstream (affected if this changes):[/bold]")
        for desc in descendants:
            state.console.print(f"  {desc}")
