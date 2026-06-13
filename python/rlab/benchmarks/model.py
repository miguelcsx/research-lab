"""Benchmark model helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from rlab._typing import JsonObject, JsonValue

SCHEMA_VERSION: Final = 1

KEY_NAME: Final = "name"
KEY_TARGET: Final = "target"
KEY_PARAMS: Final = "params"
KEY_SCHEMA_VERSION: Final = "schema_version"
KEY_BENCHMARK: Final = "benchmark"
KEY_METRICS: Final = "metrics"


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    name: str
    target: str
    params: JsonObject = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_NAME: self.name,
            KEY_TARGET: self.target,
            KEY_PARAMS: self.params,
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    benchmark: str
    target: str
    metrics: dict[str, float]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_BENCHMARK: self.benchmark,
            KEY_TARGET: self.target,
            KEY_METRICS: dict(self.metrics),
            KEY_SCHEMA_VERSION: self.schema_version,
        }
