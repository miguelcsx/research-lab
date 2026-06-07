from pathlib import Path

import typer
import yaml

from rlab.cli.state import CliState


def command(ctx: typer.Context, run: Path) -> None:
    state: CliState = ctx.obj
    manifest = yaml.safe_load((run / "run.yaml").read_text())
    state.console.print(
        {
            "run": manifest["name"],
            "parent": manifest.get("parent_run"),
            "artifacts": [str(path) for path in (run / "artifacts").rglob("*") if path.is_file()],
        }
    )
