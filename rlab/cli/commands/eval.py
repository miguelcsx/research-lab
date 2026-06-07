import typer

from rlab.cli.state import CliState
from rlab.evaluations.service import run_evaluation


def command(
    ctx: typer.Context,
    suite: str,
    model: str = typer.Option(..., "--model"),
    baseline: list[str] | None = typer.Option(None, "--baseline"),
    split: str | None = typer.Option(None),
    limit: int | None = typer.Option(None),
    batch_size: int | None = typer.Option(None, "--batch-size"),
    device: str | None = typer.Option(None),
    external_runner: str = typer.Option("local", "--external-runner"),
    save_predictions: bool = typer.Option(False, "--save-predictions"),
    upload: bool = typer.Option(False),
) -> None:
    state: CliState = ctx.obj
    state.console.print(
        run_evaluation(
            state.runtime(),
            suite,
            model,
            baselines=tuple(baseline or ()),
            split=split,
            limit=limit,
            batch_size=batch_size,
            device=device,
            external_runner=external_runner,
            save_predictions=save_predictions,
            upload=upload,
        )
    )
