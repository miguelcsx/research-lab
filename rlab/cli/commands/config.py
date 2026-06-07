import json

import typer

from rlab.cli.state import CliState

app = typer.Typer(help="Inspect effective project configuration.")


@app.command("show")
def show(ctx: typer.Context, resolved: bool = typer.Option(False, "--resolved")) -> None:
    del resolved
    state: CliState = ctx.obj
    state.console.print_json(state.runtime().config.model_dump_json())


@app.command("validate")
def validate(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.runtime()
    state.console.print("valid")


@app.command("paths")
def paths(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.console.print_json(json.dumps(state.runtime().paths.model_dump(mode="json"), indent=2))
