"""Python-facing experiment model helpers backed by Rust-compatible schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping


@dataclass(slots=True)
class RetryPolicy:
    """Retry policy for transient experiment failures."""

    max_attempts: int = 1
    on: tuple[str, ...] = ()
    delay_seconds: float = 0.0
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Experiment:
    """Declarative experiment specification."""

    name: str
    question: str | None = None
    hypothesis: str | None = None
    matrix: Mapping[str, list[Any]] = field(default_factory=dict)
    metrics: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["matrix"] = dict(self.matrix)
        return value


@dataclass(slots=True)
class ExperimentResult:
    """Normalized experiment result returned by user code or runner code."""

    metrics: dict[str, float] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Grid:
    axes: Mapping[str, list[Any]]

    def where(self, predicate: Callable[[dict[str, Any]], bool]) -> "Grid":
        rows = _expand(dict(self.axes))
        filtered: dict[str, list[Any]] = {key: [] for key in self.axes}
        for row in rows:
            if predicate(row):
                for key, value in row.items():
                    if value not in filtered[key]:
                        filtered[key].append(value)
        return Grid(filtered)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "axes": dict(self.axes)}


@dataclass(slots=True)
class Distribution:
    kind: str
    values: tuple[Any, ...] = ()
    low: float | None = None
    high: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Sample:
    space: Mapping[str, Distribution]
    n: int
    seed: int = 0
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "space": {key: value.to_dict() for key, value in self.space.items()}, "n": self.n, "seed": self.seed}


def factor(values: list[Any] | tuple[Any, ...]) -> list[Any]:
    """Return an explicit matrix factor."""
    return list(values)


def grid(axes: Mapping[str, list[Any]]) -> Grid:
    """Create a grid-search matrix helper."""
    return Grid(dict(axes))


def choice(values: list[Any] | tuple[Any, ...]) -> Distribution:
    """Create a discrete sampling distribution."""
    return Distribution(kind="choice", values=tuple(values))


def uniform(low: float, high: float) -> Distribution:
    """Create a uniform sampling distribution."""
    return Distribution(kind="uniform", low=float(low), high=float(high))


def log_uniform(low: float, high: float) -> Distribution:
    """Create a log-uniform sampling distribution."""
    return Distribution(kind="log_uniform", low=float(low), high=float(high))


def _expand(axes: dict[str, list[Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [{}]
    for key, values in axes.items():
        next_rows: list[dict[str, Any]] = []
        for row in rows:
            for value in values:
                candidate = dict(row)
                candidate[key] = value
                next_rows.append(candidate)
        rows = next_rows
    return rows
