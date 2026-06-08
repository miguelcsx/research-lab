from __future__ import annotations

import json

import typer

from rlab.adapters.service import execute_adapter
from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import EntryKind

app = typer.Typer(help="Inspect and execute registered external-tool adapters.")


@app.command("list")
def list_adapters(ctx: typer.Context) -> None:
    """List every registered adapter."""
    state: CliState = ctx.obj
    runtime = state.runtime()
    rows = [
        {
            "name": record.name,
            "version": record.version,
            "module": record.module,
            "description": record.description,
        }
        for record in runtime.registry.list(EntryKind.ADAPTER)
    ]
    state.console.print(table("Adapters", rows))


@app.command("run")
def run_adapter_command(
    ctx: typer.Context,
    name: str,
    inputs: str = typer.Option("{}", "--inputs", help="JSON object of adapter inputs"),
) -> None:
    """Run an adapter under a tracked RunSession and print the run directory."""
    state: CliState = ctx.obj
    try:
        payload = json.loads(inputs)
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"--inputs must be JSON: {error}") from error
    if not isinstance(payload, dict):
        raise typer.BadParameter("--inputs must decode to a JSON object")
    run_dir = execute_adapter(state.runtime(), name, inputs=payload)
    state.console.print(str(run_dir))


@app.command("describe")
def describe(ctx: typer.Context, name: str) -> None:
    """Show the metadata recorded for an adapter in the registry."""
    state: CliState = ctx.obj
    record = state.runtime().registry.get(EntryKind.ADAPTER, name)
    state.console.print(
        {
            "name": record.name,
            "version": record.version,
            "module": record.module,
            "qualname": record.qualname,
            "description": record.description,
            "tags": list(record.tags),
        }
    )
