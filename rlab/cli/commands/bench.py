import shutil
from pathlib import Path

import typer

from rlab.benchmarks.service import run_benchmark
from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.reporting.compare import compare_runs


def command(
    ctx: typer.Context,
    target: str,
    benchmark: str,
    data: str | None = typer.Option(None),
    params: list[str] | None = typer.Option(None, "--params"),
    output: Path | None = typer.Option(None),
    compare_with: Path | None = typer.Option(None, "--compare-with"),
    repeat: int = typer.Option(1, min=1),
    warmup: int = typer.Option(0, min=0),
) -> None:
    state: CliState = ctx.obj
    parsed = dict(item.split("=", maxsplit=1) for item in params or ())
    run = run_benchmark(
        state.runtime(),
        target,
        benchmark,
        data=data,
        params=parsed,
        repeat=repeat,
        warmup=warmup,
    )
    destination = state.root / output if output else run
    if output:
        shutil.copytree(run, destination, dirs_exist_ok=True)
    state.console.print(destination)
    if compare_with:
        state.console.print(table("Benchmark comparison", compare_runs((compare_with, run))))
