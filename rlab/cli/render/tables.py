from collections.abc import Iterable, Mapping
from typing import Any

from rich.table import Table


def table(title: str, rows: Iterable[Mapping[str, Any]]) -> Table:
    materialized = tuple(rows)
    result = Table(title=title)
    columns = tuple(dict.fromkeys(key for row in materialized for key in row))
    for column in columns:
        result.add_column(column)
    for row in materialized:
        result.add_row(*(str(row.get(column, "")) for column in columns))
    return result
