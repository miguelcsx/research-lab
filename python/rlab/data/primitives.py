"""Declarative data primitives for Python user code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from rlab._decorators import ComponentUse, DataDecision, data_boundary, data_drop, data_keep, data_update


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
    return {"kind": "patterns", "name": name, "mapping": dict(mapping)}


def substitute(field: str, old: str, new: str) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a simple record substitution transform."""
    def apply(record: Mapping[str, Any]) -> DataDecision:
        value = str(record.get(field, ""))
        updated = dict(record)
        updated[field] = value.replace(old, new)
        return data_update(updated, reason=f"substitute:{field}")
    return apply


def classify(field: str, labels: Mapping[str, str]) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Classify a record by substring labels."""
    def apply(record: Mapping[str, Any]) -> DataDecision:
        text = str(record.get(field, ""))
        updated = dict(record)
        for label, needle in labels.items():
            if needle in text:
                updated["label"] = label
                return data_update(updated, reason=f"classify:{label}")
        return data_keep(record)
    return apply


def predicate(fn: Callable[[Mapping[str, Any]], bool], reason: str = "predicate") -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a filtering predicate returning DataDecision."""
    def apply(record: Mapping[str, Any]) -> DataDecision:
        if fn(record):
            return data_keep(record)
        return data_drop(reason)
    return apply


def threshold(field: str, minimum: float | None = None, maximum: float | None = None) -> Callable[[Mapping[str, Any]], DataDecision]:
    """Create a numeric threshold filter."""
    def apply(record: Mapping[str, Any]) -> DataDecision:
        value = float(record[field])
        if minimum is not None and value < minimum:
            return data_drop(f"{field}<minimum")
        if maximum is not None and value > maximum:
            return data_drop(f"{field}>maximum")
        return data_keep(record)
    return apply


def materialize(records: Iterable[Mapping[str, Any]], stages: Iterable[Callable[[Mapping[str, Any]], DataDecision]]) -> list[Mapping[str, Any]]:
    """Apply record-level stages locally for small Python workflows."""
    output: list[Mapping[str, Any]] = []
    for record in records:
        current: Mapping[str, Any] | None = dict(record)
        for stage in stages:
            if current is None:
                break
            decision = stage(current)
            if decision.action == "drop":
                current = None
            elif decision.action in {"keep", "update"}:
                current = decision.record
            else:
                current = decision.record
        if current is not None:
            output.append(current)
    return output


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
