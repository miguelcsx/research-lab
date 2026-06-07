import json
from pathlib import Path

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.data.ablation import DataAblation
from rlab.data.compare import compare_profiles
from rlab.data.service import build, diff, profile, promote, sample, write_sample

app = typer.Typer(help="Build, validate, compare, and promote datasets.")


@app.command("build")
def build_command(ctx: typer.Context, dataset: str, version: str = "1") -> None:
    state: CliState = ctx.obj
    state.console.print(build(state.runtime(), dataset, version))


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
    count: int = typer.Option(100, "--n"),
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
