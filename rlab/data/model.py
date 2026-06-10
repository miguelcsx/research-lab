from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Generic, Protocol, TypeAlias, TypeVar

from rlab.data.context import DataContext
from rlab.data.ids import OutputId
from rlab.typing import JsonValue

RecordT = TypeVar("RecordT")
RecordT_co = TypeVar("RecordT_co", covariant=True)
SourceT_co = TypeVar("SourceT_co", covariant=True)
InputT_contra = TypeVar("InputT_contra", contravariant=True)
OutputT_co = TypeVar("OutputT_co", covariant=True)
RecordT_contra = TypeVar("RecordT_contra", contravariant=True)


class Action(StrEnum):
    KEEP = "keep"
    UPDATE = "update"
    DROP = "drop"
    BOUNDARY = "boundary"


@dataclass(frozen=True, slots=True)
class Boundary:
    reason: str
    metrics: Mapping[str, JsonValue] = field(default_factory=dict)


Item: TypeAlias = RecordT | Boundary


@dataclass(frozen=True, slots=True)
class Decision(Generic[RecordT_co]):
    action: Action
    reason: str
    record: RecordT_co | None = None
    metrics: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        requires_record = self.action in (Action.KEEP, Action.UPDATE)
        if requires_record != (self.record is not None):
            raise ValueError(f"{self.action.value} decisions require record={requires_record}")


def keep(
    record: RecordT,
    *,
    reason: str = "kept",
    metrics: Mapping[str, JsonValue] | None = None,
) -> Decision[RecordT]:
    return Decision(Action.KEEP, reason, record, metrics or {})


def update(
    record: RecordT,
    *,
    reason: str = "updated",
    metrics: Mapping[str, JsonValue] | None = None,
) -> Decision[RecordT]:
    return Decision(Action.UPDATE, reason, record, metrics or {})


def drop(
    reason: str,
    *,
    metrics: Mapping[str, JsonValue] | None = None,
) -> Decision[object]:
    return Decision(Action.DROP, reason, metrics=metrics or {})


def boundary(
    reason: str,
    *,
    metrics: Mapping[str, JsonValue] | None = None,
) -> Decision[object]:
    return Decision(Action.BOUNDARY, reason, metrics=metrics or {})


@dataclass(slots=True)
class ComponentMeta:
    kind: str
    name: str


@dataclass(frozen=True, slots=True)
class ComponentUse:
    reference: str
    configuration: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineSpec:
    name: str
    version: str
    stages: tuple[ComponentUse, ...]
    description: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuditPolicy:
    capture_decisions: bool = False
    sample_reasons: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        invalid = {reason: count for reason, count in self.sample_reasons.items() if count <= 0}
        if invalid:
            raise ValueError(f"audit sample counts must be positive: {invalid}")


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    version: str
    source: ComponentUse
    pipeline: str
    sinks: tuple[ComponentUse, ...]
    checks: tuple[ComponentUse, ...] = ()
    metrics: tuple[ComponentUse, ...] = ()
    audit: AuditPolicy = field(default_factory=AuditPolicy)
    description: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CheckResult:
    passed: bool
    failure_status: str = "error"
    metrics: Mapping[str, float] = field(default_factory=dict)
    message: str = ""

    @property
    def manifest_status(self) -> str:
        return "passed" if self.passed else self.failure_status


@dataclass(frozen=True, slots=True)
class SinkResult:
    outputs: Mapping[OutputId, Path]
    stats: Mapping[str, JsonValue] = field(default_factory=dict)
    checks: Mapping[str, str] = field(default_factory=dict)
    licenses: tuple[str, ...] = ()


class DataSource(Protocol[SourceT_co]):
    def read(self, ctx: DataContext) -> Iterable[SourceT_co]: ...


class RecordStage(Protocol[InputT_contra, OutputT_co]):
    def apply(
        self,
        record: InputT_contra,
        ctx: DataContext,
    ) -> Decision[OutputT_co]: ...


class BatchStage(Protocol[InputT_contra, OutputT_co]):
    def apply(
        self,
        records: Iterable[Item[InputT_contra]],
        ctx: DataContext,
    ) -> Iterable[Item[OutputT_co]]: ...


class DataCheck(Protocol[RecordT_contra]):
    def evaluate(
        self,
        records: Sequence[RecordT_contra],
        ctx: DataContext,
    ) -> CheckResult: ...


class DataMetric(Protocol[RecordT_contra]):
    def measure(self, records: Sequence[RecordT_contra], ctx: DataContext) -> JsonValue: ...


class DataSink(Protocol[RecordT_contra]):
    def write(self, records: Sequence[RecordT_contra], ctx: DataContext) -> SinkResult: ...
