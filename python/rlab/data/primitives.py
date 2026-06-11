"""Declarative data primitives for Python user code."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias

from rlab._decorators import (
    ComponentUse,
    DataDecision,
    data_boundary,
    data_drop,
    data_keep,
    data_update,
)

Record: TypeAlias = Mapping[str, Any]
MutableRecord: TypeAlias = dict[str, Any]
RecordStage: TypeAlias = Callable[[Mapping[str, Any]], DataDecision]


@dataclass(frozen=True, slots=True)
class DataContext:
    """Context passed to data stages."""

    params: Mapping[str, Any]
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
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DataBoundary:
    """Boundary value emitted by grouping/dedup stages."""

    value: Any
    kind: str


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    """Declarative pipeline spec."""

    name: str
    stages: tuple[ComponentUse, ...]
    version: str = "1"
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
    version: str = "1"
    tags: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a dataset check."""

    name: str
    passed: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class SinkResult:
    """Result of a dataset sink write."""

    name: str
    path: str
    records: int


@dataclass(frozen=True, slots=True)
class DataCheck:
    name: str
    fn: Callable[[Iterable[Mapping[str, Any]], DataContext], CheckResult]


@dataclass(frozen=True, slots=True)
class DataMetric:
    name: str
    fn: Callable[[Iterable[Mapping[str, Any]], DataContext], float]


@dataclass(frozen=True, slots=True)
class DataSink:
    name: str
    fn: Callable[[Iterable[Mapping[str, Any]], DataContext], SinkResult]


@dataclass(frozen=True, slots=True)
class DataAblation:
    name: str
    factors: Mapping[str, tuple[Any, ...]]


@dataclass(frozen=True, slots=True)
class DataExperiment:
    name: str
    dataset: str
    ablations: tuple[DataAblation, ...] = ()


def patterns(name: str, mapping: Mapping[str, str]) -> dict[str, Any]:
    """Build a declarative named-pattern transform descriptor."""
    return {
        "kind": "patterns",
        "name": name,
        "mapping": dict(mapping),
    }


def substitute(
    field: str, old: str, new: str
) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a simple record substitution transform."""

    def apply(record: Mapping[str, Any]) -> DataDecision:
        updated = _copy_record(record)
        updated[field] = _record_text(record, field).replace(old, new)
        return data_update(updated, reason=f"substitute:{field}")

    return apply


def classify(
    field: str, labels: Mapping[str, str]
) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Classify a record by substring labels."""

    def apply(record: Mapping[str, Any]) -> DataDecision:
        text = _record_text(record, field)
        label = _first_matching_label(text, labels)

        if label is None:
            return data_keep(record)

        updated = _copy_record(record)
        updated["label"] = label
        return data_update(updated, reason=f"classify:{label}")

    return apply


def predicate(
    fn: Callable[[Mapping[str, Any]], bool], reason: str = "predicate"
) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a filtering predicate returning DataDecision."""

    def apply(record: Mapping[str, Any]) -> DataDecision:
        return data_keep(record) if fn(record) else data_drop(reason)

    return apply


def threshold(
    field: str, minimum: float | None = None, maximum: float | None = None
) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a numeric threshold filter."""

    def apply(record: Mapping[str, Any]) -> DataDecision:
        value = float(record[field])

        if _below_minimum(value, minimum):
            return data_drop(f"{field}<minimum")

        if _above_maximum(value, maximum):
            return data_drop(f"{field}>maximum")

        return data_keep(record)

    return apply


def materialize(
    records: Iterable[Mapping[str, Any]],
    stages: Iterable[Callable[[Mapping[str, Any]], DataDecision]],
) -> list[Mapping[str, Any]]:
    """Apply record-level stages locally for small Python workflows."""
    output: list[Mapping[str, Any]] = []

    for record in records:
        materialized = _materialize_record(record, stages)
        if materialized is not None:
            output.append(materialized)

    return output


def _materialize_record(
    record: Mapping[str, Any],
    stages: Iterable[Callable[[Mapping[str, Any]], DataDecision]],
) -> Mapping[str, Any] | None:
    current: Mapping[str, Any] | None = dict(record)

    for stage in stages:
        if current is None:
            return None

        current = _apply_materialize_decision(stage(current), current)

    return current


def _apply_materialize_decision(
    decision: DataDecision,
    current: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if decision.action == "drop":
        return None

    if decision.action in {"keep", "update"}:
        return decision.record

    return decision.record


def _copy_record(record: Mapping[str, Any]) -> MutableRecord:
    return dict(record)


def _record_text(record: Mapping[str, Any], field: str) -> str:
    return str(record.get(field, ""))


def _first_matching_label(text: str, labels: Mapping[str, str]) -> str | None:
    for label, needle in labels.items():
        if needle in text:
            return label

    return None


def _below_minimum(value: float, minimum: float | None) -> bool:
    return minimum is not None and value < minimum


def _above_maximum(value: float, maximum: float | None) -> bool:
    return maximum is not None and value > maximum


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
