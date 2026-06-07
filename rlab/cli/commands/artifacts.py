from pathlib import Path

import typer

from rlab.artifacts.service import local_store, promote_path
from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.references import ReferenceKind, parse_reference

app = typer.Typer(help="Manage reusable artifacts.")


@app.command("list")
def list_artifacts(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.console.print(table("Artifacts", local_store(state.runtime()).index.list()))


def _artifact(reference: str) -> tuple[str, str, str]:
    parsed = parse_reference(reference)
    if parsed.kind is not ReferenceKind.ARTIFACT or parsed.artifact_kind is None:
        raise typer.BadParameter("Expected artifact:<kind>/<name>@<version-or-alias>")
    return parsed.artifact_kind, parsed.value, parsed.alias or "latest"


def _target(reference: str) -> tuple[str, str]:
    parsed = parse_reference(reference)
    return parsed.component_kind or parsed.kind.value, parsed.value


@app.command("describe")
def describe(ctx: typer.Context, reference: str) -> None:
    state: CliState = ctx.obj
    kind, name, version = _artifact(reference)
    row = local_store(state.runtime()).index.resolve(kind, name, version)
    if row is None:
        raise typer.BadParameter("Artifact not found")
    state.console.print(dict(row))


@app.command("promote")
def promote(
    ctx: typer.Context,
    source: Path,
    target: str = typer.Option(..., "--as"),
    version: str = typer.Option("1"),
    alias: str = typer.Option("candidate"),
) -> None:
    state: CliState = ctx.obj
    artifact_kind, name = _target(target)
    state.console.print(
        promote_path(
            state.runtime(),
            source,
            artifact_kind=artifact_kind,
            name=name,
            version=version,
            alias=alias,
        )
    )


@app.command("pull")
def pull(
    ctx: typer.Context,
    reference: str,
) -> None:
    state: CliState = ctx.obj
    kind, name, alias = _artifact(reference)
    state.console.print(local_store(state.runtime()).get(kind, name, alias))


@app.command("push")
def push(ctx: typer.Context) -> None:
    del ctx
    raise typer.BadParameter("Remote artifact push requires an installed backend adapter")


@app.command("lineage")
def lineage(ctx: typer.Context, reference: str) -> None:
    describe(ctx, reference)


@app.command("aliases")
def aliases(ctx: typer.Context) -> None:
    list_artifacts(ctx)


@app.command("deprecate")
def deprecate(ctx: typer.Context, reference: str) -> None:
    state: CliState = ctx.obj
    kind, name, version = _artifact(reference)
    local_store(state.runtime()).index.deprecate(kind, name, version)


@app.command("delete")
def delete(ctx: typer.Context, reference: str) -> None:
    state: CliState = ctx.obj
    kind, name, version = _artifact(reference)
    local_store(state.runtime()).delete(kind, name, version)
