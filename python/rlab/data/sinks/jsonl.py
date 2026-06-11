"""JSONL sink utilities for small local rlab data declarations."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class JsonlSink:
    """Write mapping records to a local JSONL file."""

    path: str | Path

    def write(self, records: Iterable[Mapping[str, Any]], _ctx: Any = None) -> Path:
        target = _target_path(self.path)
        _ensure_parent_dir(target)
        _write_jsonl(target, records)
        return target


def _target_path(path: str | Path) -> Path:
    return Path(path)


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(_jsonl_line(record))


def _jsonl_line(record: Mapping[str, Any]) -> str:
    return _json_dumps(record) + "\n"


def _json_dumps(record: Mapping[str, Any]) -> str:
    return json.dumps(dict(record), separators=(",", ":"), sort_keys=True)


__all__ = ["JsonlSink"]
