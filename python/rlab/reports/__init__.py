"""Markdown report helpers for Python callers."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any


def write_markdown_report(path: str | Path, title: str, fields: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for key, value in fields.items():
        lines.append(f"- **{key}**: {value}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


__all__ = ["write_markdown_report"]
