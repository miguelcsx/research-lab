import json
from pathlib import Path

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.data.compare import compare_profiles
from rlab.data.service import profile
from rlab.reporting.compare import compare_runs
from rlab.reporting.export import export_rows


def command(
    ctx: typer.Context,
    paths: list[Path],
    metric: str | None = typer.Option(None),
    group_by: str | None = typer.Option(None, "--group-by"),
    sort_by: str | None = typer.Option(None, "--sort-by"),
    descending: bool = typer.Option(False),
    format_name: str = typer.Option("table", "--format"),
    output: Path | None = typer.Option(None),
    baseline: str | None = typer.Option(None),
) -> None:
    state: CliState = ctx.obj
    if paths and str(paths[0]) == "datasets":
        profiles = {path.stem: profile(path) for path in paths[1:]}
        compared = compare_profiles(profiles)
        rows = [{"metric": key, **values} for key, values in compared.items()]
        _render(state, rows, format_name, output)
        return
    expanded = tuple(
        child
        for path in paths
        for child in ([path] if (path / "run.yaml").exists() else sorted(path.iterdir()))
        if (child / "run.yaml").exists()
    )
    rows = list(compare_runs(expanded))
    if metric:
        rows = [{"run": row["run"], metric: row.get(metric)} for row in rows]
    if baseline and metric:
        reference = next(
            (row.get(metric) for row in rows if row["run"] == Path(baseline).name),
            None,
        )
        if isinstance(reference, (int, float)):
            rows = [
                {
                    **row,
                    f"{metric}.delta": (
                        float(row[metric]) - reference
                        if isinstance(row.get(metric), (int, float))
                        else None
                    ),
                }
                for row in rows
            ]
    if group_by:
        rows.sort(key=lambda row: str(row.get(group_by, "")))
    if sort_by:
        rows.sort(key=lambda row: (row.get(sort_by) is None, row.get(sort_by)), reverse=descending)
    _render(state, rows, format_name, output)


def _render(
    state: CliState,
    rows: list[dict[str, object]],
    format_name: str,
    output: Path | None,
) -> None:
    if output:
        export_rows(rows, format_name, output)
    elif format_name == "json":
        state.console.print(json.dumps(rows, indent=2, default=str))
    else:
        state.console.print(table("Comparison", rows))
