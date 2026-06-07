import shutil

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState


def command(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    runtime = state.runtime()
    checks = [
        {"check": "lab.toml", "ok": (state.root / "lab.toml").exists()},
        {"check": "runs writable", "ok": runtime.paths.runs.exists()},
        {"check": "artifacts writable", "ok": runtime.paths.artifacts.exists()},
        {"check": "git", "ok": shutil.which("git") is not None},
        {"check": "uv", "ok": shutil.which("uv") is not None},
        {"check": "plugins", "ok": True},
    ]
    state.console.print(table("rlab doctor", checks))
    if not all(check["ok"] for check in checks):
        raise typer.Exit(1)
