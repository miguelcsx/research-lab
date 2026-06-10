"""Benchmark model helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class BenchmarkSpec:
    name: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkResult:
    benchmark: str
    target: str
    metrics: dict[str, float]
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
