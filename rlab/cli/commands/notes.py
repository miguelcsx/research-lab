from __future__ import annotations

import json

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState

app = typer.Typer(help="Attach and view notes on runs.")


@app.command("add")
def add_note(
    ctx: typer.Context,
    run_id: str,
    text: str,
) -> None:
    """Add a note to a run."""
    state: CliState = ctx.obj
    from rlab.journal.notes import add_note as _add
    run_dir = _find_run(state.root, run_id)
    note = _add(run_dir / "notes.jsonl", text)
    state.console.print(f"[green]Note added:[/green] {note.text}")


@app.command("list")
def list_notes(ctx: typer.Context, run_id: str) -> None:
    """List notes for a run."""
    state: CliState = ctx.obj
    from rlab.journal.notes import list_notes as _list
    run_dir = _find_run(state.root, run_id)
    notes = _list(run_dir / "notes.jsonl")
    rows = [{"timestamp": n.timestamp, "text": n.text, "author": n.author or ""} for n in notes]
    state.console.print(table("Notes", rows))


def _find_run(root: Path, run_id: str) -> Path:
    from pathlib import Path
    runs_dir = root / "runs"
    if runs_dir.exists():
        for d in runs_dir.iterdir():
            if d.is_dir() and (d.name == run_id or d.name.endswith(run_id)):
                return d
    raise typer.BadParameter(f"Run {run_id!r} not found")
