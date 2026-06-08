from __future__ import annotations

import json
import time
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import RUNS_DB_NAME, RunStatus

_DEFAULT_RUNS_LIMIT = 50
_FOLLOW_INTERVAL_SECONDS = 1.0

app = typer.Typer(help="Inspect and manage runs.")


@app.command("list")
def list_runs(
    ctx: typer.Context,
    status: Annotated[str | None, typer.Option("--status")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    limit: int = typer.Option(_DEFAULT_RUNS_LIMIT),
) -> None:
    """List runs with their status and metric summary."""
    state: CliState = ctx.obj
    from rlab.runs.index import RunIndex

    index = RunIndex(state.root / ".rlab" / RUNS_DB_NAME)
    run_status = RunStatus(status) if status else None
    rows = index.list(status=run_status, tags=tuple(tag or ()), limit=limit)
    if state.json_output:
        state.console.print(json.dumps(list(rows), indent=2, default=str))
    else:
        state.console.print(table("Runs", rows))


@app.command("show")
def show(ctx: typer.Context, run_id: str) -> None:
    """Show full metadata for a single run."""
    state: CliState = ctx.obj
    from rlab.runs.reader import RunReader

    runs_dir = state.root / "runs"
    run_dir = (
        next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None)
        if runs_dir.exists()
        else None
    )
    if run_dir is None:
        raise typer.BadParameter(f"Run {run_id!r} not found")
    reader = RunReader(run_dir)
    data: dict[str, object] = {
        "run_dir": str(run_dir),
        "params": reader.params(),
        "metrics": reader.metrics_summary(),
        "status": reader.status().value,
        "notes": [n.get("text", "") for n in reader.notes()],
    }
    if reader.layout.manifest_file.exists():
        m = reader.manifest()
        data["operation"] = m.operation
        data["tags"] = list(m.tags)
    state.console.print_json(json.dumps(data, default=str))


@app.command("logs")
def logs(ctx: typer.Context, run_id: str) -> None:
    """Stream log files from a run."""
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    run_dir = (
        next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None)
        if runs_dir.exists()
        else None
    )
    if run_dir is None:
        raise typer.BadParameter(f"Run {run_id!r} not found")
    logs_dir = run_dir / "logs"
    if not logs_dir.exists():
        state.console.print("[dim]No logs directory.[/dim]")
        return
    for log_file in sorted(logs_dir.rglob("*.*")):
        state.console.print(f"\n[bold]--- {log_file.name} ---[/bold]")
        state.console.print(log_file.read_text())


@app.command("clean")
def clean(
    ctx: typer.Context,
    failed: bool = typer.Option(False, "--failed"),
    older_than: str | None = typer.Option(None, "--older-than", help="e.g. '30d'"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Remove failed or old runs from the runs directory."""
    import shutil

    from rlab.runs.reader import RunReader

    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    if not runs_dir.exists():
        state.console.print("No runs directory.")
        return
    removed = 0
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        should_remove = False
        if failed:
            reader = RunReader(run_dir)
            if reader.status() == RunStatus.FAILED:
                should_remove = True
        if should_remove:
            state.console.print(f"{'[dry-run] ' if dry_run else ''}Removing {run_dir.name}")
            if not dry_run:
                shutil.rmtree(run_dir)
            removed += 1
    state.console.print(f"Removed {removed} run(s).")


@app.command("query")
def query(
    ctx: typer.Context,
    expr: str = typer.Argument("", help="SQL WHERE clause against the SQLite index"),
    where: Annotated[
        str | None, typer.Option("--where", help="Python predicate over run columns")
    ] = None,
    order_by: Annotated[
        str | None, typer.Option("--order-by", help="metric name, optionally with 'desc'")
    ] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
) -> None:
    """Query runs. Use SQL via the positional arg, or rich expressions via flags."""
    state: CliState = ctx.obj
    if where is not None or order_by is not None or limit is not None or not expr:
        from rlab.runs.query import collect_run_rows, filter_rows, sort_rows

        rows = collect_run_rows(state.root / "runs")
        rows = filter_rows(rows, where)
        rows = sort_rows(rows, order_by)
        if limit is not None:
            rows = rows[:limit]
        state.console.print(table("Query Results", rows))
        return
    from rlab.runs.index import RunIndex

    index = RunIndex(state.root / ".rlab" / RUNS_DB_NAME)
    state.console.print(table("Query Results", index.query(expr)))


@app.command("best")
def best(
    ctx: typer.Context,
    metric: Annotated[str, typer.Option("--metric", help="Metric to optimize")],
    group_by: Annotated[str | None, typer.Option("--group-by")] = None,
    where: Annotated[str | None, typer.Option("--where")] = None,
    minimize: Annotated[bool, typer.Option("--minimize")] = False,
) -> None:
    """Show the best run per group (or overall) for a metric."""
    state: CliState = ctx.obj
    from rlab.runs.query import collect_run_rows, filter_rows, group_best

    rows = filter_rows(collect_run_rows(state.root / "runs"), where)
    winners = group_best(rows, metric=metric, group_by=group_by, maximize=not minimize)
    state.console.print(table(f"Best by {metric}", winners))


@app.command("tail")
def tail(ctx: typer.Context, run_id: str) -> None:
    """Follow metrics.jsonl for a running experiment."""
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    run_dir = (
        next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None)
        if runs_dir.exists()
        else None
    )
    if run_dir is None:
        raise typer.BadParameter(f"Run {run_id!r} not found")
    metrics_file = run_dir / "metrics.jsonl"
    state.console.print(f"Following {metrics_file} (Ctrl+C to stop)")
    last_pos = 0
    try:
        while True:
            if metrics_file.exists():
                with metrics_file.open() as f:
                    f.seek(last_pos)
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            state.console.print(f"{rec.get('name')}: {rec.get('value')}")
                    last_pos = f.tell()
            time.sleep(_FOLLOW_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
