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
from rlab._rlab import (
    DataBoundary,
    NativeDocumentAssembler as _NativeDocumentAssembler,
    NativeSimhashDedup as _NativeSimhashDedup,
    NativeTextFilter as _NativeTextFilter,
    materialize_records,
)
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
    "FilterRule",
    "TextFilter",
    "SimhashDedup",
    "DocumentAssembler",
    "register_builtins",
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


@dataclass(frozen=True, slots=True)
class FilterRule:
    """Declarative text filter rule executed by the native data engine."""

    kind: str
    field: str = "text"
    minimum: float | None = None
    maximum: float | None = None
    markers: tuple[str, ...] = ()

    @classmethod
    def url(cls, *, field: str = "text") -> "FilterRule":
        return cls(kind="url", field=field)

    @classmethod
    def word_count(
        cls,
        *,
        field: str = "text",
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> "FilterRule":
        return cls(kind="word_count", field=field, minimum=minimum, maximum=maximum)

    @classmethod
    def symbol_ratio(
        cls,
        *,
        field: str = "text",
        maximum: float,
    ) -> "FilterRule":
        return cls(kind="symbol_ratio", field=field, maximum=maximum)

    @classmethod
    def repetition_ratio(
        cls,
        *,
        field: str = "text",
        maximum: float,
    ) -> "FilterRule":
        return cls(kind="repetition_ratio", field=field, maximum=maximum)

    @classmethod
    def boilerplate(
        cls,
        *,
        field: str = "text",
        markers: tuple[str, ...],
    ) -> "FilterRule":
        return cls(kind="boilerplate", field=field, markers=markers)

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {"kind": self.kind, "field": self.field}
        if self.minimum is not None:
            payload["minimum"] = self.minimum
        if self.maximum is not None:
            payload["maximum"] = self.maximum
        if self.markers:
            payload["markers"] = list(self.markers)
        return payload


class TextFilter:
    """Registry component wrapping native declarative text filter rules."""

    __rlab_ref__ = "filter:rlab.text"

    def __init__(self, rules: Iterable[FilterRule | Mapping[str, object]]) -> None:
        self.rules = tuple(_rule(rule) for rule in rules)
        self._native = _NativeTextFilter([rule.to_dict() for rule in self.rules])

    def apply(self, record: object, ctx: object | None = None) -> DataDecision:
        return self._native.apply(record, ctx)

    def to_dict(self) -> JsonObject:
        return {"ref": self.__rlab_ref__, "rules": [rule.to_dict() for rule in self.rules]}


class SimhashDedup:
    """Registry component for native exact and simhash near deduplication."""

    __rlab_ref__ = "dedup:rlab.simhash"

    def __init__(
        self,
        *,
        field: str = "text",
        source_field: str = "source",
        exact_min_words: int = 6,
        source_exact_min_words: Mapping[str, int] | None = None,
        near_enabled: bool = True,
        near_min_words: int = 12,
        near_hamming_threshold: int = 3,
        near_max_bucket_size: int = 64,
    ) -> None:
        self.field = field
        self.source_field = source_field
        self.exact_min_words = exact_min_words
        self.source_exact_min_words = _string_int_map(source_exact_min_words or {})
        self.near_enabled = near_enabled
        self.near_min_words = near_min_words
        self.near_hamming_threshold = near_hamming_threshold
        self.near_max_bucket_size = near_max_bucket_size
        self._native = _NativeSimhashDedup(
            field=field,
            source_field=source_field,
            exact_min_words=exact_min_words,
            source_exact_min_words=self.source_exact_min_words,
            near_enabled=near_enabled,
            near_min_words=near_min_words,
            near_hamming_threshold=near_hamming_threshold,
            near_max_bucket_size=near_max_bucket_size,
        )

    def apply(self, records: Iterable[object]) -> list[object]:
        return self._native.apply(list(records))

    def to_dict(self) -> JsonObject:
        return {
            "ref": self.__rlab_ref__,
            "field": self.field,
            "source_field": self.source_field,
            "exact_min_words": self.exact_min_words,
            "source_exact_min_words": dict(self.source_exact_min_words),
            "near_enabled": self.near_enabled,
            "near_min_words": self.near_min_words,
            "near_hamming_threshold": self.near_hamming_threshold,
            "near_max_bucket_size": self.near_max_bucket_size,
        }


class DocumentAssembler:
    """Registry component for native budget-aware text document assembly."""

    __rlab_ref__ = "group:rlab.documents"

    def __init__(
        self,
        *,
        text_field: str = "text",
        source_field: str = "source",
        origin_field: str = "origin",
        target_word_budget: int = 10_000_000,
        source_word_targets: Mapping[str, int] | None = None,
        min_document_words: int = 50,
        max_document_chars: int = 20_000,
        max_document_lines: int = 400,
    ) -> None:
        self.text_field = text_field
        self.source_field = source_field
        self.origin_field = origin_field
        self.target_word_budget = target_word_budget
        self.source_word_targets = _string_int_map(source_word_targets or {})
        self.min_document_words = min_document_words
        self.max_document_chars = max_document_chars
        self.max_document_lines = max_document_lines
        self._native = _NativeDocumentAssembler(
            text_field=text_field,
            source_field=source_field,
            origin_field=origin_field,
            target_word_budget=target_word_budget,
            source_word_targets=self.source_word_targets,
            min_document_words=min_document_words,
            max_document_chars=max_document_chars,
            max_document_lines=max_document_lines,
        )

    def apply(self, records: Iterable[object]) -> list[JsonObject]:
        return self._native.apply(list(records))

    def to_dict(self) -> JsonObject:
        return {
            "ref": self.__rlab_ref__,
            "text_field": self.text_field,
            "source_field": self.source_field,
            "origin_field": self.origin_field,
            "target_word_budget": self.target_word_budget,
            "source_word_targets": dict(self.source_word_targets),
            "min_document_words": self.min_document_words,
            "max_document_chars": self.max_document_chars,
            "max_document_lines": self.max_document_lines,
        }


def register_builtins(lab: object) -> None:
    """Register native generic data components in a project registry."""
    lab.filter("rlab.text")(TextFilter)
    lab.dedup("rlab.simhash")(SimhashDedup)
    lab.group("rlab.documents")(DocumentAssembler)


def _rule(value: FilterRule | Mapping[str, object]) -> FilterRule:
    if isinstance(value, FilterRule):
        return value
    return FilterRule(
        kind=str(value["kind"]),
        field=str(value.get("field", "text")),
        minimum=_optional_float(value.get("minimum")),
        maximum=_optional_float(value.get("maximum")),
        markers=tuple(str(item) for item in value.get("markers", ())),
    )


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _string_int_map(values: Mapping[object, int]) -> dict[str, int]:
    return {str(key): int(value) for key, value in values.items()}


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
