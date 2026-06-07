import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from rlab.reporting.markdown import markdown_table


def _latex(rows: tuple[Mapping[str, Any], ...]) -> str:
    if not rows:
        return ""
    columns = tuple(dict.fromkeys(key for row in rows for key in row))
    body = [" & ".join(str(row.get(column, "")) for column in columns) + r" \\" for row in rows]
    return "\n".join(
        (
            rf"\begin{{tabular}}{{{'l' * len(columns)}}}",
            " & ".join(columns) + r" \\",
            r"\hline",
            *body,
            r"\end{tabular}",
        )
    )


def export_rows(rows: Iterable[Mapping[str, Any]], format_name: str, output: Path) -> None:
    materialized = tuple(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        output.write_text(json.dumps(materialized, indent=2, default=str) + "\n")
    elif format_name in {"md", "markdown"}:
        output.write_text(markdown_table(materialized))
    elif format_name == "latex":
        output.write_text(_latex(materialized))
    elif format_name == "csv":
        columns = tuple(dict.fromkeys(key for row in materialized for key in row))
        with output.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(materialized)
    else:
        raise ValueError(f"Unsupported report format {format_name!r}")
