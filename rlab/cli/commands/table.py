from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.state import CliState


def command(
    ctx: typer.Context,
    rows: Annotated[str, typer.Option("--rows", help="Comma-separated row keys")],
    cols: Annotated[str, typer.Option("--cols", help="Comma-separated column keys")],
    fmt: Annotated[str, typer.Option("--format")] = "markdown",
    where: Annotated[str | None, typer.Option("--where")] = None,
    order_by: Annotated[str | None, typer.Option("--order-by")] = None,
    runs_dir: Annotated[Path | None, typer.Option("--runs-dir")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Pivot runs into a table and render it as markdown/latex/csv/typst/tsv."""
    state: CliState = ctx.obj
    from rlab.runs.query import collect_run_rows, filter_rows, sort_rows
    from rlab.tables.pivot import pivot_rows
    from rlab.tables.render import render_table

    base = runs_dir or (state.root / "runs")
    flat = sort_rows(filter_rows(collect_run_rows(base), where), order_by)
    table = pivot_rows(
        flat,
        row_keys=_split(rows),
        column_keys=_split(cols),
    )
    rendered = render_table(table, fmt)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        state.console.print(f"[green]Table written:[/green] {output}")
    else:
        state.console.print(rendered)


def _split(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(",") if part.strip())
