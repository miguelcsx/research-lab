from pathlib import Path


def render_latex_table(
    rows: list[dict[str, object]],
    *,
    caption: str = "",
    label: str = "tab:results",
) -> str:
    if not rows:
        return ""
    columns = list(rows[0].keys())
    col_spec = "|".join("l" * len(columns))
    header = " & ".join(_escape(c) for c in columns)

    lines: list[str] = [
        "\\begin{table}[h]",
        "\\centering",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\hline",
        f"{header} \\\\",
        "\\hline",
    ]
    for row in rows:
        cells = " & ".join(_escape(str(row.get(c, ""))) for c in columns)
        lines.append(f"{cells} \\\\")
    lines.extend([
        "\\hline",
        "\\end{tabular}",
    ])
    if caption:
        lines.append(f"\\caption{{{_escape(caption)}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def _escape(text: str) -> str:
    for char in ("%", "&", "#", "_", "{", "}", "~", "^"):
        text = text.replace(char, f"\\{char}")
    return text


def export_latex_table(path: Path, rows: list[dict[str, object]], **kwargs: object) -> None:
    path.write_text(render_latex_table(rows, **kwargs))  # type: ignore[arg-type]
