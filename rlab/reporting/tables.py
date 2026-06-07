from collections.abc import Iterable, Mapping
from typing import Any

from rich.table import Table


def mapping_table(title: str, rows: Iterable[Mapping[str, Any]]) -> Table:
    materialized = tuple(rows)
    table = Table(title=title)
    columns = tuple(dict.fromkeys(key for row in materialized for key in row))
    for column in columns:
        table.add_column(str(column))
    for row in materialized:
        table.add_row(*(str(row.get(column, "")) for column in columns))
    return table
