"""JSONL source utilities for small local rlab data declarations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class JsonlSource:
    """Read JSON objects from a local JSONL file."""

    path: str | Path

    def read(self, _ctx: Any = None) -> Iterator[dict[str, Any]]:
        source = Path(self.path)
        with source.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL record at line {line_number} is not an object")
                yield value


__all__ = ["JsonlSource"]
