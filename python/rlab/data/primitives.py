"""Declarative data primitives for Python user code."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Final, TypeAlias, cast

from rlab._decorators import (
    ComponentUse,
    DataDecision,
    data_boundary,
    data_drop,
    data_keep,
    data_update,
)
from rlab._rlab import materialize_records
from rlab._typing import JsonObject, JsonValue

Record: TypeAlias = Mapping[str, JsonValue]
MutableRecord: TypeAlias = JsonObject
RecordStage: TypeAlias = Callable[[Record], DataDecision]

DEFAULT_VERSION: Final = "1"
DEFAULT_DESCRIPTION: Final = ""
ACTION_DROP: Final = "drop"
FIELD_LABEL: Final = "label"

KIND_PATTERNS: Final = "patterns"
KEY_KIND: Final = "kind"
KEY_NAME: Final = "name"
KEY_MAPPING: Final = "mapping"

REASON_PREDICATE: Final = "predicate"
REASON_SUBSTITUTE: Final = "substitute:{field}"
REASON_CLASSIFY: Final = "classify:{label}"
REASON_NOT_NUMERIC: Final = "{field}:not_numeric"
REASON_BELOW_MINIMUM: Final = "{field}<minimum"
REASON_ABOVE_MAXIMUM: Final = "{field}>maximum"

__all__ = [
    "AuditPolicy",
    "CheckResult",
    "ComponentUse",
    "DataAblation",
    "DataAction",
    "DataBoundary",
    "DataCheck",
    "DataContext",
    "DataDecision",
    "DataExperiment",
    "DataMetric",
    "DataSink",
    "DataSource",
    "DatasetSpec",
    "PipelineSpec",
    "SinkResult",
    "classify",
    "data_boundary",
    "data_drop",
    "data_keep",
    "data_update",
    "materialize",
    "patterns",
    "predicate",
    "substitute",
    "threshold",
]


@dataclass(frozen=True, slots=True)
class DataContext:
    """Context passed to data stages."""

    params: Mapping[str, JsonValue]
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class DataSource:
    """Declarative data source descriptor."""

    name: str
    ref: str


@dataclass(frozen=True, slots=True)
class DataAction:
    """Named data action descriptor."""

    name: str
    params: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class DataBoundary:
    """Boundary value emitted by grouping/dedup stages."""

    value: object
    kind: str


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    """Declarative pipeline spec."""

    name: str
    stages: tuple[ComponentUse, ...]
    version: str = DEFAULT_VERSION
    tags: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True, slots=True)
class AuditPolicy:
    """Dataset audit capture policy."""

    capture_decisions: bool = False
    sample_reasons: Mapping[str, int] | None = None


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Declarative dataset build spec."""

    name: str
    source: ComponentUse
    pipeline: str
    sinks: tuple[ComponentUse, ...] = ()
    checks: tuple[ComponentUse, ...] = ()
    metrics: tuple[ComponentUse, ...] = ()
    audit: AuditPolicy | None = None
    version: str = DEFAULT_VERSION
    tags: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a dataset check."""

    name: str
    passed: bool
    message: str = DEFAULT_DESCRIPTION


@dataclass(frozen=True, slots=True)
class SinkResult:
    """Result of a dataset sink write."""

    name: str
    path: str
    records: int


@dataclass(frozen=True, slots=True)
class DataCheck:
    name: str
    fn: Callable[[Iterable[Record], DataContext], CheckResult]


@dataclass(frozen=True, slots=True)
class DataMetric:
    name: str
    fn: Callable[[Iterable[Record], DataContext], float]


@dataclass(frozen=True, slots=True)
class DataSink:
    name: str
    fn: Callable[[Iterable[Record], DataContext], SinkResult]


@dataclass(frozen=True, slots=True)
class DataAblation:
    name: str
    factors: Mapping[str, tuple[JsonValue, ...]]


@dataclass(frozen=True, slots=True)
class DataExperiment:
    name: str
    dataset: str
    ablations: tuple[DataAblation, ...] = ()


def patterns(name: str, mapping: Mapping[str, str]) -> JsonObject:
    """Build a declarative named-pattern transform descriptor."""
    return {
        KEY_KIND: KIND_PATTERNS,
        KEY_NAME: name,
        KEY_MAPPING: dict(mapping),
    }


def substitute(field: str, old: str, new: str) -> Callable[[Record], DataDecision]:
    """Create a simple record substitution transform."""

    def apply(record: Record) -> DataDecision:
        updated = _copy_record(record)
        updated[field] = _record_text(record, field).replace(old, new)
        return data_update(updated, reason=_format(REASON_SUBSTITUTE, field=field))

    return apply


def classify(field: str, labels: Mapping[str, str]) -> Callable[[Record], DataDecision]:
    """Classify a record by substring labels."""

    def apply(record: Record) -> DataDecision:
        label = _first_matching_label(_record_text(record, field), labels)
        if label is None:
            return data_keep(record)

        updated = _copy_record(record)
        updated[FIELD_LABEL] = label
        return data_update(updated, reason=_format(REASON_CLASSIFY, label=label))

    return apply


def predicate(
    fn: Callable[[Record], bool],
    reason: str = REASON_PREDICATE,
) -> Callable[[Record], DataDecision]:
    """Create a filtering predicate returning DataDecision."""

    def apply(record: Record) -> DataDecision:
        if fn(record):
            return data_keep(record)
        return data_drop(reason)

    return apply


def threshold(
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> Callable[[Record], DataDecision]:
    """Create a numeric threshold filter."""

    def apply(record: Record) -> DataDecision:
        value = _numeric_value(record[field])
        if value is None:
            return data_drop(_format(REASON_NOT_NUMERIC, field=field))
        if minimum is not None and value < minimum:
            return data_drop(_format(REASON_BELOW_MINIMUM, field=field))
        if maximum is not None and value > maximum:
            return data_drop(_format(REASON_ABOVE_MAXIMUM, field=field))
        return data_keep(record)

    return apply


def materialize(
    records: Iterable[Record],
    stages: Iterable[RecordStage],
) -> list[Record]:
    """Apply record-level stages through the native rlab data engine."""
    return cast(list[Record], list(materialize_records(list(records), list(stages))))


def _copy_record(record: Record) -> MutableRecord:
    return dict(record)


def _record_text(record: Record, field: str) -> str:
    return str(record.get(field, DEFAULT_DESCRIPTION))


def _first_matching_label(text: str, labels: Mapping[str, str]) -> str | None:
    return next((label for label, needle in labels.items() if needle in text), None)


def _numeric_value(value: JsonValue) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None

    if isinstance(value, str) and not value.strip():
        return None

    return float(value)


def _format(template: str, **values: str) -> str:
    return template.format(**values)
