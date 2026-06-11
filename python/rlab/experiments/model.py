"""Python-facing experiment model helpers backed by Rust-compatible schemas."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, TypeAlias

JsonDict: TypeAlias = dict[str, Any]
AxisMap: TypeAlias = Mapping[str, list[Any]]
MutableAxisMap: TypeAlias = dict[str, list[Any]]
ExpandedRow: TypeAlias = dict[str, Any]


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
        filtered = _empty_axes_like(self.axes)

        for row in _expand(dict(self.axes)):
            if predicate(row):
                _append_unique_axis_values(filtered, row)

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
        return {
            "schema_version": self.schema_version,
            "space": _distribution_space_to_dict(self.space),
            "n": self.n,
            "seed": self.seed,
        }


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
    return _bounded_distribution("uniform", low, high)


def log_uniform(low: float, high: float) -> Distribution:
    """Create a log-uniform sampling distribution."""
    return _bounded_distribution("log_uniform", low, high)


def _bounded_distribution(kind: str, low: float, high: float) -> Distribution:
    return Distribution(kind=kind, low=float(low), high=float(high))


def _distribution_space_to_dict(space: Mapping[str, Distribution]) -> dict[str, Any]:
    return {key: value.to_dict() for key, value in space.items()}


def _empty_axes_like(axes: AxisMap) -> MutableAxisMap:
    return {key: [] for key in axes}


def _append_unique_axis_values(axes: MutableAxisMap, row: Mapping[str, Any]) -> None:
    for key, value in row.items():
        if value not in axes[key]:
            axes[key].append(value)


def _expand(axes: dict[str, list[Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [{}]

    for key, values in axes.items():
        rows = _expand_axis(rows, key, values)

    return rows


def _expand_axis(
    rows: Iterable[ExpandedRow],
    key: str,
    values: Iterable[Any],
) -> list[ExpandedRow]:
    return [_with_axis_value(row, key, value) for row in rows for value in values]


def _with_axis_value(row: Mapping[str, Any], key: str, value: Any) -> ExpandedRow:
    return {**row, key: value}
