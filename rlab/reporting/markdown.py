from collections.abc import Iterable, Mapping
from typing import Any


def markdown_table(rows: Iterable[Mapping[str, Any]]) -> str:
    materialized = tuple(rows)
    if not materialized:
        return ""
    columns = tuple(dict.fromkeys(key for row in materialized for key in row))
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in materialized
    ]
    return "\n".join((header, separator, *body)) + "\n"
