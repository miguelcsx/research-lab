from __future__ import annotations

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.graph.store import KnowledgeGraph

_DEFAULT_LINEAGE_DEPTH = 5
app = typer.Typer(help="Research knowledge graph: build, query, lineage.")


def _graph(state: CliState) -> KnowledgeGraph:
    return KnowledgeGraph(state.root / ".rlab" / "graph.db")


@app.command("build")
def build(ctx: typer.Context) -> None:
    """Index runs and artifacts into the knowledge graph."""
    state: CliState = ctx.obj
    graph = _graph(state)
    count = 0

    runs_dir = state.root / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            graph.add_node(f"run:{run_dir.name}", "run", run_dir.name)
            count += 1

    state.console.print(f"[green]Graph built:[/green] {count} nodes indexed.")


@app.command("query")
def query(ctx: typer.Context, sql: str) -> None:
    """Execute a SQL query against the knowledge graph."""
    state: CliState = ctx.obj
    graph = _graph(state)
    rows = graph.query(sql)
    state.console.print(table("Graph Query", rows))


@app.command("lineage")
def lineage(ctx: typer.Context, subject: str, depth: int = typer.Option(5)) -> None:
    """Show lineage graph for a subject."""
    state: CliState = ctx.obj
    graph = _graph(state)
    edges = graph.lineage(subject, depth=depth)
    if not edges:
        state.console.print(f"[dim]No lineage for {subject!r}.[/dim]")
        return
    state.console.print(f"\n[bold]Lineage of {subject}:[/bold]")
    for src, tgt in edges:
        state.console.print(f"  {src} → {tgt}")
