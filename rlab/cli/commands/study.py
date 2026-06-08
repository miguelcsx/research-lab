from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.studies.loader import load_study
from rlab.studies.report import render_study_report
from rlab.studies.store import StudyStore

app = typer.Typer(help="Manage research studies (questions, hypotheses, decisions).")


def _store(state: CliState) -> StudyStore:
    return StudyStore(state.root / ".rlab" / "studies.db")


@app.command("new")
def new(
    ctx: typer.Context,
    question: str,
    name: Annotated[str | None, typer.Option("--name", help="Slug used as the study id")] = None,
    domain: Annotated[str, typer.Option("--domain")] = "general",
    decision_rule: Annotated[str, typer.Option("--decision-rule")] = "",
) -> None:
    """Record a new study question (no Python file required)."""
    state: CliState = ctx.obj
    slug = name or _slug(question)
    _store(state).upsert(slug, question, domain=domain, decision_rule=decision_rule)
    state.console.print(f"[green]Study registered:[/green] {slug}")


@app.command("link")
def link(
    ctx: typer.Context,
    study_name: str,
    run_id: str,
    note: Annotated[str, typer.Option("--note")] = "",
) -> None:
    """Associate a run directory or run id with a study."""
    state: CliState = ctx.obj
    _store(state).link_run(study_name, run_id, notes=note)
    state.console.print(f"[green]Linked:[/green] {run_id} → {study_name}")


@app.command("list")
def list_studies(ctx: typer.Context) -> None:
    """List every recorded study."""
    state: CliState = ctx.obj
    state.console.print(table("Studies", _store(state).list()))


@app.command("report")
def report(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Render a markdown report for a `@rlab.study` file and its linked runs."""
    state: CliState = ctx.obj
    runtime = state.runtime()
    name, study_def = load_study(runtime.registry, path)
    linked = _store(state).runs_for(name)
    runs_dir = state.root / "runs"
    paths = tuple(runs_dir / row["run_id"] for row in linked if (runs_dir / row["run_id"]).exists())
    text = render_study_report(name, study_def, paths)
    target = output or (state.root / "reports" / f"study_{name}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    state.console.print(f"[green]Report written:[/green] {target}")


def _slug(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in value.strip().lower())
    return cleaned.strip("_") or "study"
