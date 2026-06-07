from datetime import timedelta

import typer

from rlab.cache.cleanup import clean_cache
from rlab.cache.manager import CacheManager
from rlab.cli.state import CliState

app = typer.Typer(help="Inspect and clean disposable cache data.")


@app.command("list")
def list_cache(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    for path in CacheManager(state.runtime().paths.cache).entries():
        state.console.print(path)


@app.command("path")
def cache_path(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    state.console.print(state.runtime().paths.cache)


@app.command("inspect")
def inspect(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    manager = CacheManager(state.runtime().paths.cache)
    state.console.print({"files": len(manager.entries()), "bytes": manager.size()})


@app.command("clean")
def clean(
    ctx: typer.Context,
    older_than: int | None = typer.Option(None, help="Age in days"),
) -> None:
    state: CliState = ctx.obj
    age = timedelta(days=older_than) if older_than is not None else None
    for path in clean_cache(state.runtime().paths.cache, age):
        state.console.print(path)


@app.command("prune")
def prune(ctx: typer.Context, area: str) -> None:
    state: CliState = ctx.obj
    target = state.runtime().paths.cache / area
    for path in clean_cache(target):
        state.console.print(path)
