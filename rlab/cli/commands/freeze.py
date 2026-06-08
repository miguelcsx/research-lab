from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.state import CliState

app = typer.Typer(help="Paper/release: freeze, lock, export runs.")


@app.command("run")
def freeze_run_cmd(
    ctx: typer.Context,
    run_path: Annotated[Path, typer.Argument()],
    name: Annotated[str, typer.Option("--as", "-n")],
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Create a frozen, named copy of a run."""
    state: CliState = ctx.obj
    from rlab.reports.export import freeze_run

    output_dir = output or state.root / "paper"
    dest = freeze_run(run_path, name, output_dir)
    state.console.print(f"[green]Frozen:[/green] {dest}")


@app.command("lock")
def lock_cmd(ctx: typer.Context, run_path: Path) -> None:
    """Lock a run against further modification."""
    from rlab.reports.export import is_locked, lock_run

    if is_locked(run_path):
        typer.echo(f"{run_path.name} is already locked.")
        return
    lock_run(run_path)
    typer.echo(f"Locked: {run_path.name}")


@app.command("export")
def export_cmd(
    ctx: typer.Context,
    run_path: Annotated[Path, typer.Argument()],
    fmt: Annotated[str, typer.Option("--format")] = "repro-zip",
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Export a run for sharing or reproduction."""
    from rlab.reports.export import export_repro_zip

    if fmt == "repro-zip":
        out = export_repro_zip(run_path, output)
        typer.echo(f"Exported: {out}")
    else:
        raise typer.BadParameter(f"Unknown format {fmt!r}; available: repro-zip")


@app.command("methods")
def methods_cmd(ctx: typer.Context, run_path: Path) -> None:
    """Generate a draft methods section from run metadata."""
    from rlab.reports.export import generate_methods_section

    typer.echo(generate_methods_section(run_path))
