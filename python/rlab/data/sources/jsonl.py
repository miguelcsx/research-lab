"""JSONL source utilities for small local rlab data declarations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rlab._typing import JsonObject, JsonValue

ENCODING: Final = "utf-8"
READ_MODE: Final = "r"
FIRST_LINE_NUMBER: Final = 1

ERROR_RECORD_NOT_OBJECT: Final = "JSONL record at line {line_number} is not an object"
ERROR_VALUE_NOT_JSON: Final = "JSONL value is not JSON-compatible"

__all__ = ["JsonlSource"]


@dataclass(frozen=True, slots=True)
class JsonlSource:
    """Read JSON objects from a local JSONL file."""

    path: str | Path

    def read(self, _ctx: object = None) -> Iterator[JsonObject]:
        with Path(self.path).open(READ_MODE, encoding=ENCODING) as file:
            for line_number, line in enumerate(file, start=FIRST_LINE_NUMBER):
                stripped = line.strip()
                if not stripped:
                    continue

                yield _json_object_from_line(stripped, line_number)


def _json_object_from_line(line: str, line_number: int) -> JsonObject:
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError(ERROR_RECORD_NOT_OBJECT.format(line_number=line_number))

    return {str(key): _json_value(item) for key, item in value.items()}


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str):
        return value

    if isinstance(value, bool):
        return value

    if isinstance(value, int | float):
        return value

    if isinstance(value, list):
        return [_json_value(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}

    raise TypeError(ERROR_VALUE_NOT_JSON)
