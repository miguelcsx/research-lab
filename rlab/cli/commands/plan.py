from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.state import CliState

app = typer.Typer(help="Plan and estimate experiments before running.")


@app.command("power")
def power(
    ctx: typer.Context,
    effect_size: Annotated[float, typer.Option("--effect-size")] = 0.05,
    variance: Annotated[float, typer.Option("--variance")] = 1.0,
    alpha: Annotated[float, typer.Option("--alpha")] = 0.05,
    power_target: Annotated[float, typer.Option("--power")] = 0.80,
) -> None:
    """Estimate required repetitions to detect an effect."""
    from rlab.power import estimate_required_repetitions
    n = estimate_required_repetitions(
        effect_size, variance, alpha=alpha, power=power_target
    )
    typer.echo(
        f"To detect effect_size={effect_size} (variance={variance}, α={alpha}, power={power_target}):\n"
        f"  Minimum repetitions per condition: {n}"
    )


@app.command("cost")
def cost(
    ctx: typer.Context,
    experiment: Annotated[Path, typer.Argument()],
    seconds_per_job: Annotated[float, typer.Option()] = 3600.0,
    gpus_per_job: Annotated[float, typer.Option()] = 0.0,
    storage_gb_per_job: Annotated[float, typer.Option()] = 1.0,
    gpu_hour_cost: Annotated[float | None, typer.Option()] = None,
) -> None:
    """Estimate compute and storage budget for an experiment."""
    state: CliState = ctx.obj
    runtime = state.runtime()
    from rlab.experiments.plan import build_plan
    from rlab.experiments.loader import load_experiment
    from rlab.power import estimate_budget

    name, exp = load_experiment(runtime.registry, experiment)
    plan = build_plan(name, exp)

    budget = estimate_budget(
        plan.job_count,
        seconds_per_job=seconds_per_job,
        gpus_per_job=gpus_per_job,
        storage_gb_per_job=storage_gb_per_job,
        gpu_hour_cost_usd=gpu_hour_cost,
    )

    typer.echo(f"Experiment: {name}")
    typer.echo(f"  Total jobs: {budget.total_jobs}")
    typer.echo(f"  Estimated wall time: {budget.estimated_wall_hours:.1f}h")
    typer.echo(f"  Estimated GPU hours: {budget.estimated_gpu_hours:.1f}h")
    typer.echo(f"  Estimated storage: {budget.estimated_storage_gb:.1f}GB")
    if budget.estimated_cost_usd is not None:
        typer.echo(f"  Estimated cost: ${budget.estimated_cost_usd:.2f}")
