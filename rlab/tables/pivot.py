from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict


class PivotedTable(BaseModel):
    """A rectangular table addressable by row + column names."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


def pivot_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    row_keys: tuple[str, ...],
    column_keys: tuple[str, ...],
) -> PivotedTable:
    """Project flat run rows into a (rows × cols) table.

    Each input row contributes one output row keyed by the values of `row_keys`.
    Output columns are `row_keys + column_keys`; missing cells render as "".
    """
    columns = (*row_keys, *column_keys)
    output: list[tuple[Any, ...]] = []
    for row in rows:
        output.append(tuple(_format(row.get(key)) for key in columns))
    return PivotedTable(columns=columns, rows=tuple(output))


def _format(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return value
