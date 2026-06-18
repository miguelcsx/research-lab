"""Python-facing experiment model helpers backed by Rust-compatible schemas."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import product
from typing import Final, TypeAlias, cast

from rlab._typing import JsonObject, JsonValue

AxisMap: TypeAlias = Mapping[str, list[JsonValue]]
MutableAxisMap: TypeAlias = dict[str, list[JsonValue]]
ExpandedRow: TypeAlias = dict[str, JsonValue]

SCHEMA_VERSION: Final = 1
DEFAULT_VERSION: Final = "1"
DEFAULT_DELAY_SECONDS: Final = 0.0
DEFAULT_SEED: Final = 0

KIND_CHOICE: Final = "choice"
KIND_UNIFORM: Final = "uniform"
KIND_LOG_UNIFORM: Final = "log_uniform"

KEY_SCHEMA_VERSION: Final = "schema_version"
KEY_MAX_ATTEMPTS: Final = "max_attempts"
KEY_ON: Final = "on"
KEY_DELAY_SECONDS: Final = "delay_seconds"
KEY_NAME: Final = "name"
KEY_QUESTION: Final = "question"
KEY_HYPOTHESIS: Final = "hypothesis"
KEY_PARAMS: Final = "params"
KEY_MATRIX: Final = "matrix"
KEY_METRICS: Final = "metrics"
KEY_SEEDS: Final = "seeds"
KEY_RETRY: Final = "retry"
KEY_DATA: Final = "data"
KEY_AXES: Final = "axes"
KEY_KIND: Final = "kind"
KEY_VALUES: Final = "values"
KEY_LOW: Final = "low"
KEY_HIGH: Final = "high"
KEY_SPACE: Final = "space"
KEY_N: Final = "n"
KEY_SEED: Final = "seed"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry policy for transient experiment failures."""

    max_attempts: int = 1
    on: tuple[str, ...] = ()
    delay_seconds: float = DEFAULT_DELAY_SECONDS
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_MAX_ATTEMPTS: self.max_attempts,
            KEY_ON: list(self.on),
            KEY_DELAY_SECONDS: self.delay_seconds,
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class Experiment:
    """Declarative experiment specification."""

    name: str
    question: str | None = None
    hypothesis: str | None = None
    params: Mapping[str, JsonValue] = field(default_factory=dict)
    matrix: AxisMap = field(default_factory=dict)
    metrics: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_NAME: self.name,
            KEY_QUESTION: self.question,
            KEY_HYPOTHESIS: self.hypothesis,
            KEY_PARAMS: dict(self.params),
            KEY_MATRIX: cast(JsonValue, _axes_to_dict(self.matrix)),
            KEY_METRICS: list(self.metrics),
            KEY_SEEDS: list(self.seeds),
            KEY_RETRY: self.retry.to_dict(),
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Normalized experiment result returned by user code or runner code."""

    metrics: dict[str, float] = field(default_factory=dict)
    data: JsonObject = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_METRICS: _metrics(self.metrics),
            KEY_DATA: dict(self.data),
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class Grid:
    axes: AxisMap

    def where(self, predicate: Callable[[JsonObject], bool]) -> "Grid":
        filtered = _empty_axes_like(self.axes)

        for row in _expanded_rows(self.axes):
            if predicate(row):
                _append_unique_axis_values(filtered, row)

        return Grid(filtered)

    def to_dict(self) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: SCHEMA_VERSION,
            KEY_AXES: cast(JsonValue, _axes_to_dict(self.axes)),
        }


@dataclass(frozen=True, slots=True)
class Distribution:
    kind: str
    values: tuple[JsonValue, ...] = ()
    low: float | None = None
    high: float | None = None

    def to_dict(self) -> JsonObject:
        return {
            KEY_KIND: self.kind,
            KEY_VALUES: list(self.values),
            KEY_LOW: self.low,
            KEY_HIGH: self.high,
        }


@dataclass(frozen=True, slots=True)
class Sample:
    space: Mapping[str, Distribution]
    n: int
    seed: int = DEFAULT_SEED
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: self.schema_version,
            KEY_SPACE: _distribution_space_to_dict(self.space),
            KEY_N: self.n,
            KEY_SEED: self.seed,
        }


def factor(values: list[JsonValue] | tuple[JsonValue, ...]) -> list[JsonValue]:
    """Return an explicit matrix factor."""
    return list(values)


def grid(axes: AxisMap) -> Grid:
    """Create a grid-search matrix helper."""
    return Grid(_axes_to_dict(axes))


def choice(values: list[JsonValue] | tuple[JsonValue, ...]) -> Distribution:
    """Create a discrete sampling distribution."""
    return Distribution(kind=KIND_CHOICE, values=tuple(values))


def uniform(low: float, high: float) -> Distribution:
    """Create a uniform sampling distribution."""
    return _bounded_distribution(KIND_UNIFORM, low, high)


def log_uniform(low: float, high: float) -> Distribution:
    """Create a log-uniform sampling distribution."""
    return _bounded_distribution(KIND_LOG_UNIFORM, low, high)


def _bounded_distribution(kind: str, low: float, high: float) -> Distribution:
    return Distribution(kind=kind, low=float(low), high=float(high))


def _distribution_space_to_dict(space: Mapping[str, Distribution]) -> JsonObject:
    return {key: distribution.to_dict() for key, distribution in space.items()}


def _axes_to_dict(axes: AxisMap) -> MutableAxisMap:
    return {key: list(values) for key, values in axes.items()}


def _empty_axes_like(axes: AxisMap) -> MutableAxisMap:
    return {key: [] for key in axes}


def _append_unique_axis_values(
    axes: MutableAxisMap,
    row: Mapping[str, JsonValue],
) -> None:
    for key, value in row.items():
        values = axes[key]
        if value not in values:
            values.append(value)


def _expanded_rows(axes: AxisMap) -> Iterator[ExpandedRow]:
    if not axes:
        yield {}
        return

    keys = tuple(axes)
    for values in product(*(axes[key] for key in keys)):
        yield dict(zip(keys, values, strict=True))


def _metrics(metrics: Mapping[str, float]) -> JsonObject:
    return dict(metrics)
