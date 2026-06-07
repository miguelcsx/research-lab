from __future__ import annotations

from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState

app = typer.Typer(help="Manage experiment baselines.")


def _store(state: CliState):
    from rlab.baseline.store import BaselineStore
    return BaselineStore(state.root / ".rlab" / "baselines.db")


@app.command("add")
def add(
    ctx: typer.Context,
    name: str,
    metric: Annotated[str, typer.Option("--metric")],
    value: Annotated[float, typer.Option("--value")],
    run_id: Annotated[str | None, typer.Option("--run")] = None,
    description: Annotated[str, typer.Option("--description")] = "",
) -> None:
    """Register a named baseline result."""
    state: CliState = ctx.obj
    from rlab.baseline.model import BaselineEntry
    store = _store(state)
    entry = BaselineEntry(
        name=name, metric=metric, value=value,
        run_id=run_id, description=description,
        for_project=state.root.name,
    )
    store.add(entry)
    state.console.print(f"[green]Baseline registered:[/green] {name} ({metric}={value})")


@app.command("list")
def list_baselines(ctx: typer.Context) -> None:
    """List all registered baselines."""
    state: CliState = ctx.obj
    store = _store(state)
    baselines = store.list(for_project=state.root.name)
    rows = [
        {"name": b.name, "metric": b.metric, "value": str(b.value), "run": b.run_id or "", "description": b.description}
        for b in baselines
    ]
    state.console.print(table("Baselines", rows))


@app.command("compare")
def compare(
    ctx: typer.Context,
    run_id: str,
) -> None:
    """Compare a run's metrics against all registered baselines."""
    state: CliState = ctx.obj
    store = _store(state)
    from rlab.runs.reader import RunReader
    runs_dir = state.root / "runs"
    run_dir = next(
        (d for d in runs_dir.iterdir() if d.is_dir() and (d.name == run_id or d.name.endswith(run_id))),
        None,
    ) if runs_dir.exists() else None
    if run_dir is None:
        raise typer.BadParameter(f"Run {run_id!r} not found")
    metrics = RunReader(run_dir).metrics_summary()
    baselines = store.list()
    rows = []
    for b in baselines:
        run_val = metrics.get(b.metric)
        delta = (run_val - b.value) if run_val is not None and b.value is not None else None
        rows.append({
            "baseline": b.name,
            "metric": b.metric,
            "baseline_value": str(b.value),
            "run_value": str(run_val) if run_val is not None else "-",
            "delta": f"{delta:+.4g}" if delta is not None else "-",
        })
    state.console.print(table(f"Baseline comparison: {run_dir.name}", rows))
