"""JSONL source utilities for small local rlab data declarations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class JsonlSource:
    """Read JSON objects from a local JSONL file."""

    path: str | Path

    def read(self, _ctx: Any = None) -> Iterator[dict[str, Any]]:
        source = _source_path(self.path)

        with source.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if _is_blank_line(line):
                    continue

                yield _json_object_from_line(line, line_number)


def _source_path(path: str | Path) -> Path:
    return Path(path)


def _is_blank_line(line: str) -> bool:
    return not line.strip()


def _json_object_from_line(line: str, line_number: int) -> dict[str, Any]:
    value = json.loads(line.strip())

    if not isinstance(value, dict):
        raise ValueError(f"JSONL record at line {line_number} is not an object")

    return value


__all__ = ["JsonlSource"]
