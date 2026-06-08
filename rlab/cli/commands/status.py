import subprocess

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import RUNS_DB_NAME
from rlab.runs.index import RunIndex

_DEFAULT_STATUS_LIMIT = 10


def command(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    runtime = state.runtime()
    dirty = bool(
        subprocess.run(
            ("git", "status", "--porcelain"),
            cwd=state.root,
            text=True,
            capture_output=True,
            check=False,
        ).stdout
    )
    state.console.print(
        {
            "project": runtime.config.project.name,
            "tracking": runtime.config.tracking.backend,
            "artifacts": runtime.config.artifacts.backend,
            "git_dirty": dirty,
        }
    )
    state.console.print(
        table(
            "Recent runs",
            RunIndex(runtime.paths.cache / RUNS_DB_NAME).list(limit=_DEFAULT_STATUS_LIMIT),
        )
    )
