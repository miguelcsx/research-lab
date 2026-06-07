import json

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import EntryKind


def command(
    ctx: typer.Context,
    kind: str | None = typer.Argument(None),
) -> None:
    state: CliState = ctx.obj
    selected = EntryKind(kind.rstrip("s")) if kind else None
    records = state.runtime().registry.list(selected)
    rows = [
        {
            "kind": record.kind.value,
            "name": record.name,
            "version": record.version,
            "namespace": record.namespace,
            "module": record.module,
            "plugin": record.plugin,
            "description": record.description,
            "tags": ",".join(record.tags),
        }
        for record in records
    ]
    if state.json_output:
        state.console.print(json.dumps(rows, indent=2))
    else:
        state.console.print(table("Registry", rows))
