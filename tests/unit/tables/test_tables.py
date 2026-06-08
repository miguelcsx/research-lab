from __future__ import annotations

from rlab.tables.pivot import PivotedTable, pivot_rows
from rlab.tables.render import render_table


def test_pivot_rows() -> None:
    rows = [
        {"model": "a", "seed": 1, "score": 0.5},
        {"model": "b", "seed": 1, "score": 0.6},
    ]
    table = pivot_rows(rows, row_keys=("model",), column_keys=("score",))
    assert isinstance(table, PivotedTable)
    assert table.columns == ("model", "score")
    assert len(table.rows) == 2


def test_render_markdown() -> None:
    table = PivotedTable(columns=("a", "b"), rows=((1, 2),))
    out = render_table(table, "markdown")
    assert "| a | b |" in out


def test_render_unsupported_format_raises() -> None:
    table = PivotedTable(columns=(), rows=())
    try:
        render_table(table, "html")
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "html" in str(exc)
