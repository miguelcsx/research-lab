from __future__ import annotations

import typer

from rlab.cli.state import CliState

app = typer.Typer(help="CI integration: smoke, regression checks, reproducibility gate.")


@app.command("smoke")
def smoke(ctx: typer.Context) -> None:
    """Run quick smoke checks: config valid, modules load, discover works."""
    state: CliState = ctx.obj
    failures: list[str] = []

    # Config valid
    try:
        runtime = state.runtime()
        state.console.print("[green]✓[/green] config valid")
    except Exception as exc:
        failures.append(f"config: {exc}")
        state.console.print(f"[red]✗[/red] config: {exc}")
        raise typer.Exit(1)

    # Modules load
    from rlab.project.loader import load_modules
    from rlab.registry.context import using_registry
    from rlab.registry.store import Registry
    registry = Registry()
    with using_registry(registry):
        results = load_modules(state.root, runtime.config.modules.load)
    failed_mods = [r for r in results if not r.loaded]
    if failed_mods:
        for r in failed_mods:
            failures.append(f"module {r.name}: {r.error}")
            state.console.print(f"[red]✗[/red] module {r.name}: {r.error}")
    else:
        state.console.print(f"[green]✓[/green] {len(results)} module(s) loaded")

    # Discover
    records = runtime.registry.list()
    state.console.print(f"[green]✓[/green] {len(records)} component(s) registered")

    if failures:
        raise typer.Exit(1)
    state.console.print("\n[bold green]Smoke check passed.[/bold green]")


@app.command("compare")
def compare(
    ctx: typer.Context,
    baseline: str = typer.Option(..., "--baseline"),
    candidate: str = typer.Option(..., "--candidate"),
    metric: str = typer.Option(..., "--metric"),
    threshold: float = typer.Option(0.01, "--threshold"),
) -> None:
    """Compare candidate run against baseline; fail on regression."""
    from pathlib import Path
    state: CliState = ctx.obj
    from rlab.runs.reader import RunReader

    def _find(name: str) -> Path | None:
        runs_dir = state.root / "runs"
        if not runs_dir.exists():
            return None
        return next((d for d in runs_dir.iterdir() if d.name == name or d.name.endswith(name)), None)

    base_dir = _find(baseline)
    cand_dir = _find(candidate)
    if not base_dir or not cand_dir:
        raise typer.BadParameter("One or both run directories not found")

    base_metrics = RunReader(base_dir).metrics_summary()
    cand_metrics = RunReader(cand_dir).metrics_summary()

    base_val = base_metrics.get(metric)
    cand_val = cand_metrics.get(metric)

    if base_val is None or cand_val is None:
        state.console.print(f"[yellow]Metric {metric!r} not found in one or both runs.[/yellow]")
        return

    delta = cand_val - base_val
    state.console.print(f"{metric}: baseline={base_val:.6g}, candidate={cand_val:.6g}, delta={delta:+.6g}")

    if abs(delta) > threshold:
        state.console.print(f"[red]Regression detected: |delta| {abs(delta):.4g} > threshold {threshold}[/red]")
        raise typer.Exit(1)
    state.console.print("[green]No regression detected.[/green]")


@app.command("reproducibility-check")
def reproducibility_check(ctx: typer.Context) -> None:
    """Fail if any recent run has dirty git state or missing lockfile."""
    from pathlib import Path
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    if not runs_dir.exists():
        state.console.print("[dim]No runs directory.[/dim]")
        return

    failures: list[str] = []
    for run_dir in sorted(runs_dir.iterdir())[-10:]:  # check last 10
        if not run_dir.is_dir():
            continue
        git_file = run_dir / "reproducibility" / "git.json"
        if git_file.exists():
            import json
            data = json.loads(git_file.read_text())
            if data.get("dirty", False):
                failures.append(f"{run_dir.name}: dirty git state")
        lockfile = run_dir / "reproducibility" / "lockfile"
        if (run_dir / "run.yaml").exists() and not lockfile.exists():
            failures.append(f"{run_dir.name}: missing lockfile")

    if failures:
        for f in failures:
            state.console.print(f"[red]✗[/red] {f}")
        raise typer.Exit(1)
    state.console.print("[green]Reproducibility check passed.[/green]")
