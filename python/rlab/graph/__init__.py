"""Lineage graph helpers for lightweight Python use."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(slots=True)
class LineageEdge:
    source: str
    target: str
    reason: str | None = None


def _lineage_path(root: str | Path) -> Path:
    return Path(root).joinpath(".rlab", "cache", "lineage.jsonl")


def add_edge(root: str | Path, source: str, target: str, reason: str | None = None) -> LineageEdge:
    path = _lineage_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    edge = {"schema_version": 1, "from": source, "to": target, "reason": reason}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(edge, sort_keys=True) + "\n")
    return LineageEdge(source=source, target=target, reason=reason)


def lineage(root: str | Path, reference: str) -> dict[str, list[str]]:
    path = _lineage_path(root)
    upstream: list[str] = []
    downstream: list[str] = []
    if not path.exists():
        return {"upstream": upstream, "downstream": downstream}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            edge = json.loads(line)
            if edge.get("to") == reference:
                upstream.append(str(edge.get("from")))
            if edge.get("from") == reference:
                downstream.append(str(edge.get("to")))
    return {"upstream": upstream, "downstream": downstream}


__all__ = ["LineageEdge", "add_edge", "lineage"]
