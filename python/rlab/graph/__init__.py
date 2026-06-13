"""Lineage graph helpers — thin Python wrapper over the Rust implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from rlab._rlab import add_lineage_edge as _add_lineage_edge
from rlab._rlab import lineage_for as _lineage_for

LineageResult: TypeAlias = dict[str, list[str]]

KEY_UPSTREAM: str = "upstream"
KEY_DOWNSTREAM: str = "downstream"

__all__ = ["LineageEdge", "add_edge", "lineage"]


@dataclass(frozen=True, slots=True)
class LineageEdge:
    source: str
    target: str
    reason: str | None = None


def add_edge(
    root: str | Path,
    source: str,
    target: str,
    reason: str | None = None,
) -> LineageEdge:
    _add_lineage_edge(Path(root), source, target, reason)
    return LineageEdge(source=source, target=target, reason=reason)


def lineage(root: str | Path, reference: str) -> LineageResult:
    return _lineage_for(Path(root), reference)
