import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.project.loader import load_modules
from rlab.registry.context import using_registry
from rlab.registry.store import Registry

app = typer.Typer(help="Inspect and manage project module loading.")


@app.command("list")
def list_modules(ctx: typer.Context) -> None:
    """List all modules declared in lab.toml and their load status."""
    state: CliState = ctx.obj
    config = state.runtime().config
    registry = Registry()
    with using_registry(registry):
        results = load_modules(state.root, config.modules.load)
    rows = [
        {
            "module": r.name,
            "status": "loaded" if r.loaded else "failed",
            "kinds": ", ".join(r.registered_kinds) if r.registered_kinds else "-",
            "error": r.error or "",
        }
        for r in results
    ]
    state.console.print(table("Project Modules", rows))


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    """Verify all declared modules load without errors."""
    state: CliState = ctx.obj
    config = state.runtime().config
    registry = Registry()
    with using_registry(registry):
        results = load_modules(state.root, config.modules.load)
    failed = [r for r in results if not r.loaded]
    rows = [
        {"module": r.name, "ok": r.loaded, "error": r.error or ""}
        for r in results
    ]
    state.console.print(table("Module Health", rows))
    if failed:
        state.console.print(f"[red]{len(failed)} module(s) failed to load.[/red]")
        raise typer.Exit(1)
    state.console.print("[green]All modules loaded successfully.[/green]")


@app.command("reload")
def reload_modules(ctx: typer.Context) -> None:
    """Force-reload all declared modules (clears sys.modules entries first)."""
    import sys

    state: CliState = ctx.obj
    config = state.runtime().config
    for name in config.modules.load:
        sys.modules.pop(name, None)
    registry = Registry()
    with using_registry(registry):
        results = load_modules(state.root, config.modules.load)
    state.console.print(f"Reloaded {sum(r.loaded for r in results)}/{len(results)} modules.")
