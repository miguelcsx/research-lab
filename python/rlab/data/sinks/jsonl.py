"""JSONL sink utilities for small local rlab data declarations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class JsonlSink:
    """Write mapping records to a local JSONL file."""

    path: str | Path

    def write(self, records: Iterable[Mapping[str, Any]], _ctx: Any = None) -> Path:
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(dict(record), separators=(",", ":"), sort_keys=True))
                file.write("\n")
        return target


__all__ = ["JsonlSink"]
