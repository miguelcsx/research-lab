"""Markdown report helpers for Python callers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Final

from rlab._typing import JsonValue

ENCODING: Final = "utf-8"
NEWLINE: Final = "\n"
TRAILING_NEWLINE: Final = "\n"

MARKDOWN_HEADING_1: Final = "# {title}"
MARKDOWN_HEADING_2: Final = "## {section}"
MARKDOWN_FIELD: Final = "- **{key}**: {value}"
MARKDOWN_BLANK: Final = ""

ESCAPED_CHARS: Final = frozenset("\\`*_{}[]()#+-.!|>")

__all__ = ["write_card", "write_markdown_report"]


def write_markdown_report(
    path: str | Path,
    title: str,
    fields: Mapping[str, JsonValue],
) -> Path:
    output = Path(path)
    _write_markdown(output, _report_lines(title, fields))
    return output


def write_card(
    path: str | Path,
    *,
    title: str,
    sections: Mapping[str, Mapping[str, JsonValue]],
) -> Path:
    output = Path(path)
    _write_markdown(output, _card_lines(title, sections))
    return output


def _write_markdown(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_document(lines), encoding=ENCODING)


def _document(lines: Iterable[str]) -> str:
    return NEWLINE.join(lines).rstrip() + TRAILING_NEWLINE


def _report_lines(title: str, fields: Mapping[str, JsonValue]) -> Iterator[str]:
    yield _heading_1(title)
    yield MARKDOWN_BLANK
    yield from _field_lines(fields)


def _card_lines(
    title: str,
    sections: Mapping[str, Mapping[str, JsonValue]],
) -> Iterator[str]:
    yield _heading_1(title)
    yield MARKDOWN_BLANK

    for section, fields in sections.items():
        yield _heading_2(section)
        yield MARKDOWN_BLANK
        yield from _field_lines(fields)
        yield MARKDOWN_BLANK


def _field_lines(fields: Mapping[str, JsonValue]) -> Iterator[str]:
    for key, value in fields.items():
        yield MARKDOWN_FIELD.format(key=_inline(key), value=_inline(value))


def _heading_1(value: object) -> str:
    return MARKDOWN_HEADING_1.format(title=_heading_text(value))


def _heading_2(value: object) -> str:
    return MARKDOWN_HEADING_2.format(section=_heading_text(value))


def _heading_text(value: object) -> str:
    return _inline(value).replace(NEWLINE, " ")


def _inline(value: object) -> str:
    return "".join(_escaped_char(char) for char in str(value))


def _escaped_char(char: str) -> str:
    if char in ESCAPED_CHARS:
        return f"\\{char}"
    return char
