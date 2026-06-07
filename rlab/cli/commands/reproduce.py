from pathlib import Path

import typer

from rlab.cli.state import CliState
from rlab.reproducibility.service import reproduce


def command(
    ctx: typer.Context,
    run: Path,
    dry_run: bool = typer.Option(False, "--dry-run"),
    strict: bool = typer.Option(False),
    allow_dirty: bool = typer.Option(False, "--allow-dirty"),
    checkout: bool = typer.Option(False),
    use_current_env: bool = typer.Option(False, "--use-current-env"),
    container: bool = typer.Option(False),
) -> None:
    state: CliState = ctx.obj
    run_dir = (
        state.runtime().paths.runs / str(run).removeprefix("run:")
        if str(run).startswith("run:")
        else run
    )
    state.console.print(
        reproduce(
            state.runtime(),
            run_dir,
            dry_run=dry_run,
            strict=strict,
            allow_dirty=allow_dirty,
            checkout=checkout,
            use_current_env=use_current_env,
            container=container,
        )
    )
