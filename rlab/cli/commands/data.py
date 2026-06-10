import json
from pathlib import Path

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.config.overrides import parse_overrides
from rlab.data.ablation import DataAblation
from rlab.data.compare import compare_profiles
from rlab.data.service import (
    audit_samples,
    audit_summary,
    audit_table,
    build,
    diff,
    profile,
    promote,
    sample,
    write_sample,
)

_DEFAULT_SAMPLE_COUNT = 100
_DEFAULT_EXPLORE_COUNT = 20
_OVERRIDE_HELP = "Typed component override (path=value, repeatable)"
app = typer.Typer(help="Build, validate, compare, and promote datasets.")


@app.command("explore")
def explore_command(
    ctx: typer.Context,
    dataset: str,
    n: int = typer.Option(_DEFAULT_EXPLORE_COUNT, "--n", help="Number of sample records to show"),
    override: list[str] | None = typer.Option(None, "--override", "-o", help=_OVERRIDE_HELP),
) -> None:
    """Build a dataset then immediately show profile stats and sample records."""
    state: CliState = ctx.obj
    run_root = build(state.runtime(), dataset, overrides=parse_overrides(override or ()))
    manifest_path = run_root / "artifacts" / "dataset" / "manifest.yaml"
    prof = profile(manifest_path)
    samples = sample(manifest_path, n)
    state.console.rule(f"[bold]{dataset}[/bold] — profile")
    state.console.print_json(json.dumps(prof, default=str))
    state.console.rule(f"[bold]{dataset}[/bold] — {n} samples")
    for i, record in enumerate(samples, 1):
        state.console.print(f"[dim]{i:>3}.[/dim] {json.dumps(record, ensure_ascii=False)}")


@app.command("build")
def build_command(
    ctx: typer.Context,
    dataset: str,
    override: list[str] | None = typer.Option(None, "--override", "-o", help=_OVERRIDE_HELP),
) -> None:
    state: CliState = ctx.obj
    state.console.print(
        build(state.runtime(), dataset, overrides=parse_overrides(override or ()))
    )


@app.command("audit")
def audit_command(ctx: typer.Context, run: Path) -> None:
    state: CliState = ctx.obj
    state.console.print_json(json.dumps(audit_summary(run)))


@app.command("reasons")
def reasons_command(ctx: typer.Context, run: Path) -> None:
    state: CliState = ctx.obj
    state.console.print(table("Data drop reasons", audit_table(run, "reasons")))


@app.command("stage-summary")
def stage_summary_command(ctx: typer.Context, run: Path) -> None:
    state: CliState = ctx.obj
    state.console.print(table("Data stage summary", audit_table(run, "stages")))


@app.command("source-summary")
def source_summary_command(ctx: typer.Context, run: Path) -> None:
    state: CliState = ctx.obj
    state.console.print(table("Data source summary", audit_table(run, "sources")))


@app.command("sample-drops")
def sample_drops_command(ctx: typer.Context, run: Path, reason: str) -> None:
    state: CliState = ctx.obj
    try:
        samples = audit_samples(run, reason)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="reason") from exc
    state.console.print_json(json.dumps(samples))


@app.command("profile")
def profile_command(ctx: typer.Context, manifest: Path) -> None:
    state: CliState = ctx.obj
    state.console.print_json(json.dumps(profile(manifest), default=str))


@app.command("validate")
def validate(ctx: typer.Context, manifest: Path) -> None:
    state: CliState = ctx.obj
    result = profile(manifest)
    state.console.print(f"valid: {result['records']} records")


@app.command("diff")
def diff_command(ctx: typer.Context, left: Path, right: Path) -> None:
    state: CliState = ctx.obj
    result = diff(left, right)
    state.console.print_json(json.dumps(result, default=str))


@app.command("compare")
def compare(ctx: typer.Context, manifests: list[Path]) -> None:
    state: CliState = ctx.obj
    result = compare_profiles({path.stem: profile(path) for path in manifests})
    rows = [{"metric": key, **value} for key, value in result.items()]
    state.console.print(table("Dataset comparison", rows))


@app.command("ablate")
def ablate(ctx: typer.Context, base: str, factor: list[str] = typer.Option(...)) -> None:
    state: CliState = ctx.obj
    factors = {item.split("=", 1)[0]: item.split("=", 1)[1].split(",") for item in factor}
    result = DataAblation(base=base, factors=factors).variants()
    state.console.print_json(json.dumps(result))


@app.command("sample")
def sample_command(
    ctx: typer.Context,
    manifest: Path,
    count: int = typer.Option(_DEFAULT_SAMPLE_COUNT, "--n"),
    output: Path | None = typer.Option(None),
) -> None:
    state: CliState = ctx.obj
    records = sample(manifest, count)
    if output:
        write_sample(output, records)
    else:
        state.console.print_json(json.dumps(records))


@app.command("lineage")
def lineage(ctx: typer.Context, manifest: Path) -> None:
    state: CliState = ctx.obj
    state.console.print(manifest.read_text())


@app.command("promote")
def promote_command(
    ctx: typer.Context,
    manifest: Path,
    name: str = typer.Option(..., "--as"),
    alias: str = typer.Option(...),
) -> None:
    state: CliState = ctx.obj
    state.console.print(promote(state.runtime(), manifest, name=name, alias=alias))
