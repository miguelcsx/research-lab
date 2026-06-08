from __future__ import annotations

import csv
import io

from rlab.tables.pivot import PivotedTable

_FORMATS = ("markdown", "latex", "csv", "typst", "tsv")


def render_table(table: PivotedTable, fmt: str) -> str:
    """Render a `PivotedTable` to text in the requested format."""
    if fmt not in _FORMATS:
        raise ValueError(f"Unsupported table format {fmt!r}; choose from {_FORMATS}")
    renderer = {
        "markdown": _markdown,
        "latex": _latex,
        "csv": _csv,
        "tsv": _tsv,
        "typst": _typst,
    }[fmt]
    return renderer(table)


def _markdown(table: PivotedTable) -> str:
    header = "| " + " | ".join(table.columns) + " |"
    sep = "| " + " | ".join("---" for _ in table.columns) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in table.rows]
    return "\n".join((header, sep, *body)) + "\n"


def _latex(table: PivotedTable) -> str:
    column_spec = "l" * len(table.columns)
    lines = [
        "\\begin{table}",
        "\\centering",
        f"\\begin{{tabular}}{{{column_spec}}}",
        "\\hline",
        " & ".join(table.columns) + " \\\\",
        "\\hline",
    ]
    lines += [" & ".join(str(cell) for cell in row) + " \\\\" for row in table.rows]
    lines += ["\\hline", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines) + "\n"


def _csv(table: PivotedTable) -> str:
    return _delimited(table, ",")


def _tsv(table: PivotedTable) -> str:
    return _delimited(table, "\t")


def _delimited(table: PivotedTable, delimiter: str) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(table.columns)
    for row in table.rows:
        writer.writerow(row)
    return buffer.getvalue()


def _typst(table: PivotedTable) -> str:
    column_count = len(table.columns)
    lines = [f"#table(columns: {column_count},"]
    lines.append("  " + ", ".join(f"[*{col}*]" for col in table.columns) + ",")
    for row in table.rows:
        lines.append("  " + ", ".join(f"[{cell}]" for cell in row) + ",")
    lines.append(")")
    return "\n".join(lines) + "\n"
