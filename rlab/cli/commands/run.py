from pathlib import Path

import typer

from rlab.cli.launch import launch_run
from rlab.cli.state import CliState
from rlab.experiments.plan import ExecutionPlan
from rlab.experiments.service import run_experiment


def command(
    ctx: typer.Context,
    experiment: Path,
    dry_run: bool = typer.Option(False, "--dry-run"),
    set_values: list[str] | None = typer.Option(None, "--set"),
    seed: int | None = typer.Option(None),
    name: str | None = typer.Option(None),
    tags: list[str] | None = typer.Option(None),
    notes: str | None = typer.Option(None),
    launcher: str = typer.Option("local"),
    resume: Path | None = typer.Option(None),
    only: str | None = typer.Option(None),
) -> None:
    state: CliState = ctx.obj
    overrides = tuple(set_values or ())
    runtime = state.runtime(overrides)
    if launcher != "local":
        state.console.print(launch_run(state, launcher, experiment, only=only))
        return
    if resume is not None and not resume.exists():
        raise typer.BadParameter(f"Resume run does not exist: {resume}")
    result = run_experiment(
        runtime,
        experiment,
        dry_run=dry_run,
        only=only,
        tags=tuple(tags or ()),
        notes=notes or name,
        seed=seed,
        run_name=name,
        resume=resume,
    )
    if isinstance(result, ExecutionPlan):
        state.console.print_json(result.model_dump_json())
    else:
        state.console.print(result)
