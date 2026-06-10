from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar, cast

from rlab.constants import EntryKind
from rlab.data.components import instantiate_component
from rlab.data.context import DataContext
from rlab.data.decorators import filter, transform
from rlab.data.model import ComponentUse, Decision, drop, keep, update
from rlab.registry.store import Registry
from rlab.typing import JsonValue

RecordT = TypeVar("RecordT")


class RegexMode(StrEnum):
    SEARCH = "search"
    FULLMATCH = "fullmatch"
    MATCH = "match"


class ComparisonOperator(StrEnum):
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


@dataclass(frozen=True, slots=True)
class RegexSubstitution:
    pattern: str
    replacement: str


@dataclass(frozen=True, slots=True)
class ClassificationRule:
    label: str
    pattern: str
    mode: RegexMode = RegexMode.SEARCH


def substitute(
    name: str,
    *,
    field: str,
    substitutions: tuple[RegexSubstitution, ...],
    patterns: str | None = None,
    version: str = "1.0.0",
    registry: Registry,
) -> Callable[[type[Any]], type[Any]]:
    def decorate(marker: type[Any]) -> type[Any]:
        @dataclass(frozen=True, slots=True)
        class RegexTransform:
            def apply(
                self,
                record: Mapping[str, JsonValue],
                _ctx: DataContext,
            ) -> Decision[dict[str, JsonValue]]:
                value = record.get(field)
                if not isinstance(value, str):
                    raise TypeError(f"{field!r} must contain a string")
                pattern_values = resolve_patterns(patterns, _ctx) if patterns else {}
                updated = value
                for substitution in substitutions:
                    pattern = pattern_values.get(substitution.pattern, substitution.pattern)
                    updated = re.sub(pattern, substitution.replacement, updated)
                result = dict(record)
                result[field] = updated
                return update(result, reason="regex_substitution")

        RegexTransform.__name__ = marker.__name__
        RegexTransform.__qualname__ = marker.__qualname__
        transform(name, version=version, registry=registry)(RegexTransform)
        return marker

    return decorate


def classify(  # noqa: PLR0913
    name: str,
    *,
    field: str,
    output_field: str,
    rules: tuple[ClassificationRule, ...],
    fallback: str,
    patterns: str | None = None,
    version: str = "1.0.0",
    registry: Registry,
) -> Callable[[type[Any]], type[Any]]:
    def decorate(marker: type[Any]) -> type[Any]:
        @dataclass(frozen=True, slots=True)
        class RegexClassifier:
            def apply(
                self,
                record: Mapping[str, JsonValue],
                _ctx: DataContext,
            ) -> Decision[dict[str, JsonValue]]:
                value = record.get(field)
                if not isinstance(value, str):
                    raise TypeError(f"{field!r} must contain a string")
                pattern_values = resolve_patterns(patterns, _ctx) if patterns else {}
                label = fallback
                for rule in rules:
                    matcher = getattr(re, rule.mode.value)
                    pattern = pattern_values.get(rule.pattern, rule.pattern)
                    if matcher(pattern, value):
                        label = rule.label
                        break
                result = dict(record)
                result[output_field] = label
                return update(result, reason=f"classified:{label}")

        RegexClassifier.__name__ = marker.__name__
        RegexClassifier.__qualname__ = marker.__qualname__
        transform(name, version=version, registry=registry)(RegexClassifier)
        return marker

    return decorate


def predicate(
    name: str,
    *,
    predicate: Callable[[RecordT], bool],
    reason: str,
    version: str = "1.0.0",
    registry: Registry,
) -> Callable[[type[Any]], type[Any]]:
    _require_named(predicate)

    def decorate(marker: type[Any]) -> type[Any]:
        @dataclass(frozen=True, slots=True)
        class PredicateFilter:
            def apply(self, record: RecordT, _ctx: DataContext) -> Decision[RecordT]:
                if predicate(record):
                    return cast(Decision[RecordT], drop(reason))
                return keep(record)

        PredicateFilter.__name__ = marker.__name__
        PredicateFilter.__qualname__ = marker.__qualname__
        filter(name, version=version, registry=registry)(PredicateFilter)
        return marker

    return decorate


def threshold(  # noqa: PLR0913
    name: str,
    *,
    metric: Callable[[RecordT], float],
    metric_name: str,
    operator: ComparisonOperator,
    threshold: float,
    reason: str,
    version: str = "1.0.0",
    registry: Registry,
) -> Callable[[type[Any]], type[Any]]:
    _require_named(metric)

    def decorate(marker: type[Any]) -> type[Any]:
        @dataclass(frozen=True, slots=True)
        class MetricFilter:
            def apply(self, record: RecordT, _ctx: DataContext) -> Decision[RecordT]:
                value = metric(record)
                metrics = {metric_name: value}
                if _compare(value, operator, threshold):
                    return cast(Decision[RecordT], drop(reason, metrics=metrics))
                return keep(record, metrics=metrics)

        MetricFilter.__name__ = marker.__name__
        MetricFilter.__qualname__ = marker.__qualname__
        filter(name, version=version, registry=registry)(MetricFilter)
        return marker

    return decorate


def resolve_patterns(reference: str, ctx: DataContext) -> Mapping[str, str]:
    _, instance = instantiate_component(
        ctx.runtime.registry,
        ComponentUse(reference),
        expected=(EntryKind.PATTERNS,),
    )
    values = {
        field.name: getattr(instance, field.name)
        for field in getattr(instance, "__dataclass_fields__", {}).values()
    }
    if not all(isinstance(value, str) for value in values.values()):
        raise TypeError("pattern set fields must all be strings")
    return cast(Mapping[str, str], values)


def _compare(value: float, operator: ComparisonOperator, threshold: float) -> bool:
    if operator is ComparisonOperator.GREATER_THAN:
        return value > threshold
    if operator is ComparisonOperator.GREATER_THAN_OR_EQUAL:
        return value >= threshold
    if operator is ComparisonOperator.LESS_THAN:
        return value < threshold
    return value <= threshold


def _require_named(fn: Callable[..., object]) -> None:
    if fn.__name__ == "<lambda>":
        raise ValueError("declarative data utilities require a named function")
