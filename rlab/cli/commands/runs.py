from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import RunStatus

app = typer.Typer(help="Inspect and manage runs.")


@app.command("list")
def list_runs(
    ctx: typer.Context,
    status: Annotated[str | None, typer.Option("--status")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    limit: int = typer.Option(50),
) -> None:
    """List runs with their status and metric summary."""
    state: CliState = ctx.obj
    from rlab.runs.index import RunIndex
    index = RunIndex(state.root / ".rlab" / "runs.db")
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
    run_dir = next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None) if runs_dir.exists() else None
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
    try:
        m = reader.manifest()
        data["operation"] = m.operation
        data["tags"] = list(m.tags)
    except Exception:
        pass
    state.console.print_json(json.dumps(data, default=str))


@app.command("logs")
def logs(ctx: typer.Context, run_id: str) -> None:
    """Stream log files from a run."""
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    run_dir = next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None) if runs_dir.exists() else None
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
            try:
                reader = RunReader(run_dir)
                if reader.status() == RunStatus.FAILED:
                    should_remove = True
            except Exception:
                pass
        if should_remove:
            state.console.print(f"{'[dry-run] ' if dry_run else ''}Removing {run_dir.name}")
            if not dry_run:
                shutil.rmtree(run_dir)
            removed += 1
    state.console.print(f"Removed {removed} run(s).")


@app.command("query")
def query(ctx: typer.Context, expr: str) -> None:
    """Query runs using a SQL WHERE expression."""
    state: CliState = ctx.obj
    from rlab.runs.index import RunIndex
    index = RunIndex(state.root / ".rlab" / "runs.db")
    rows = index.query(expr)
    state.console.print(table("Query Results", rows))


@app.command("tail")
def tail(ctx: typer.Context, run_id: str) -> None:
    """Follow metrics.jsonl for a running experiment."""
    import time
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    run_dir = next((d for d in runs_dir.iterdir() if d.name.endswith(run_id) or d.name == run_id), None) if runs_dir.exists() else None
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
            time.sleep(1)
    except KeyboardInterrupt:
        pass
