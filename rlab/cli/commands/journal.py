from __future__ import annotations

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState

app = typer.Typer(help="Research journal: decisions, negatives, ideas.")

decision_app = typer.Typer(help="Record and review decisions.")
negative_app = typer.Typer(help="Track negative results.")
ideas_app = typer.Typer(help="Manage the research idea backlog.")

app.add_typer(decision_app, name="decision")
app.add_typer(negative_app, name="negative")
app.add_typer(ideas_app, name="ideas")


@decision_app.command("add")
def decision_add(
    ctx: typer.Context, rationale: str, run_id: str | None = typer.Option(None)
) -> None:
    state: CliState = ctx.obj
    from rlab.journal.decisions import add_decision

    d = add_decision(state.root / ".rlab" / "decisions.jsonl", rationale, selected_run=run_id)
    state.console.print(f"[green]Decision recorded.[/green] Rationale: {d.rationale}")


@decision_app.command("list")
def decision_list(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    from rlab.journal.decisions import list_decisions

    decisions = list_decisions(state.root / ".rlab" / "decisions.jsonl")
    rows = [
        {"created_at": d.created_at, "run": d.selected_run or "", "rationale": d.rationale}
        for d in decisions
    ]
    state.console.print(table("Decisions", rows))


@negative_app.command("add")
def negative_add(
    ctx: typer.Context,
    hypothesis: str,
    tried: str,
    reason: str,
) -> None:
    state: CliState = ctx.obj
    from rlab.journal.negative import add_negative

    add_negative(state.root / ".rlab" / "negatives.jsonl", hypothesis, tried, reason)
    state.console.print("[green]Negative result recorded.[/green]")


@negative_app.command("list")
def negative_list(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    from rlab.journal.negative import list_negatives

    entries = list_negatives(state.root / ".rlab" / "negatives.jsonl")
    rows = [{"hypothesis": e.hypothesis, "tried": e.tried, "reason": e.reason} for e in entries]
    state.console.print(table("Negative Results", rows))


@negative_app.command("search")
def negative_search(ctx: typer.Context, text: str) -> None:
    state: CliState = ctx.obj
    from rlab.journal.negative import search_negatives

    entries = search_negatives(state.root / ".rlab" / "negatives.jsonl", text)
    rows = [{"hypothesis": e.hypothesis, "tried": e.tried, "reason": e.reason} for e in entries]
    state.console.print(table(f'Negative Results matching "{text}"', rows))


@ideas_app.command("add")
def idea_add(ctx: typer.Context, text: str) -> None:
    state: CliState = ctx.obj
    from rlab.journal.ideas import add_idea

    idea = add_idea(state.root / ".rlab" / "ideas.jsonl", text)
    state.console.print(f"[green]Idea added:[/green] [{idea.id}] {idea.text}")


@ideas_app.command("list")
def idea_list(ctx: typer.Context, status: str | None = typer.Option(None)) -> None:
    from rlab.constants import IdeaStatus

    state: CliState = ctx.obj
    from rlab.journal.ideas import list_ideas

    idea_status = IdeaStatus(status) if status else None
    ideas = list_ideas(state.root / ".rlab" / "ideas.jsonl", status=idea_status)
    rows = [{"id": i.id, "status": i.status.value, "text": i.text} for i in ideas]
    state.console.print(table("Ideas", rows))


@ideas_app.command("promote")
def idea_promote(ctx: typer.Context, idea_id: str, status: str) -> None:
    from rlab.constants import IdeaStatus

    state: CliState = ctx.obj
    from rlab.journal.ideas import promote_idea

    idea = promote_idea(
        state.root / ".rlab" / "ideas.jsonl",
        idea_id,
        status=IdeaStatus(status),
    )
    if idea:
        state.console.print(f"[green]Idea {idea_id} promoted to {status}.[/green]")
    else:
        raise typer.BadParameter(f"Idea {idea_id!r} not found")
