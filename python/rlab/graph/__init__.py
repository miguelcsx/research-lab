"""Lineage graph helpers for lightweight Python use."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

LineageResult: TypeAlias = dict[str, list[str]]
LineageRecord: TypeAlias = dict[str, Any]


@dataclass(slots=True)
class LineageEdge:
    source: str
    target: str
    reason: str | None = None


def _lineage_path(root: str | Path) -> Path:
    return Path(root).joinpath(".rlab", "cache", "lineage.jsonl")


def add_edge(
    root: str | Path, source: str, target: str, reason: str | None = None
) -> LineageEdge:
    path = _lineage_path(root)
    _ensure_parent_dir(path)

    edge = _lineage_record(source=source, target=target, reason=reason)
    _append_jsonl(path, edge)

    return LineageEdge(source=source, target=target, reason=reason)


def lineage(root: str | Path, reference: str) -> dict[str, list[str]]:
    upstream: list[str] = []
    downstream: list[str] = []

    for edge in _iter_lineage_records(_lineage_path(root)):
        if edge.get("to") == reference:
            upstream.append(str(edge.get("from")))

        if edge.get("from") == reference:
            downstream.append(str(edge.get("to")))

    return {"upstream": upstream, "downstream": downstream}


def _lineage_record(source: str, target: str, reason: str | None) -> LineageRecord:
    return {
        "schema_version": 1,
        "from": source,
        "to": target,
        "reason": reason,
    }


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(record))


def _jsonl_line(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True) + "\n"


def _iter_lineage_records(path: Path) -> Iterator[LineageRecord]:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if _is_blank_line(line):
                continue

            yield json.loads(line)


def _is_blank_line(line: str) -> bool:
    return not line.strip()


__all__ = ["LineageEdge", "add_edge", "lineage"]
