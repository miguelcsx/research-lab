import json
import subprocess

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.plugins.entrypoints import installed_entrypoints, metadata_for
from rlab.plugins.loader import load_installed_plugins

app = typer.Typer(help="Inspect and validate installed plugins.")


@app.command("list")
def list_plugins(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    metadata = tuple(metadata_for(item) for item in installed_entrypoints())
    state.console.print(table("Plugins", [item.model_dump() for item in metadata]))


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    metadata = load_installed_plugins(state.runtime().registry)
    state.console.print(table("Plugin health", [item.model_dump() for item in metadata]))
    if any(item.error for item in metadata):
        raise typer.Exit(1)


@app.command("describe")
def describe(ctx: typer.Context, name: str) -> None:
    state: CliState = ctx.obj
    item = next(
        (
            metadata_for(entrypoint)
            for entrypoint in installed_entrypoints()
            if entrypoint.name == name
        ),
        None,
    )
    if item is None:
        raise typer.BadParameter(f"Unknown plugin {name!r}")
    state.console.print_json(item.model_dump_json())


@app.command("entrypoints")
def entrypoint_list(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.console.print(
        json.dumps(
            {entrypoint.name: entrypoint.value for entrypoint in installed_entrypoints()},
            indent=2,
        )
    )


@app.command("conflicts")
def conflicts(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.console.print_json(json.dumps(state.runtime().registry.conflicts()))


@app.command("add")
@app.command("install")
def add(ctx: typer.Context, package: str) -> None:
    state: CliState = ctx.obj
    subprocess.run(("uv", "add", package), cwd=state.root, check=True)
