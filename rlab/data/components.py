from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Any, get_type_hints

from pydantic import TypeAdapter, ValidationError

from rlab.constants import EntryKind
from rlab.data.model import ComponentUse, DatasetSpec, PipelineSpec
from rlab.errors import ConfigError, RegistryError
from rlab.references import parse_reference
from rlab.registry.records import RegistryRecord
from rlab.registry.store import Registry
from rlab.typing import JsonValue

SOURCE_OVERRIDE_PARTS = 2
COMPONENT_OVERRIDE_PARTS = 3

REFERENCE_KINDS: dict[str, EntryKind] = {
    kind.value: kind
    for kind in (
        EntryKind.SOURCE,
        EntryKind.TRANSFORM,
        EntryKind.FILTER,
        EntryKind.GROUP,
        EntryKind.DEDUP,
        EntryKind.SINK,
        EntryKind.CHECK,
        EntryKind.METRIC,
        EntryKind.PIPELINE,
        EntryKind.DATASET,
        EntryKind.PATTERNS,
    )
}


def component_record(
    registry: Registry,
    component: ComponentUse,
    *,
    expected: tuple[EntryKind, ...],
) -> RegistryRecord:
    reference = parse_reference(component.reference)
    kind = REFERENCE_KINDS.get(reference.kind.value)
    if kind is None or kind not in expected:
        choices = ", ".join(item.value for item in expected)
        raise RegistryError(f"{component.reference!r} must reference one of: {choices}")
    return registry.get(kind, reference.value)


def instantiate_component(
    registry: Registry,
    component: ComponentUse,
    *,
    expected: tuple[EntryKind, ...],
) -> tuple[RegistryRecord, Any]:
    record = component_record(registry, component, expected=expected)
    cls = record.value
    if not isinstance(cls, type) or not is_dataclass(cls):
        raise TypeError(f"{component.reference} must resolve to a dataclass type")
    declared_fields = {field.name: field for field in fields(cls)}
    unknown = set(component.configuration) - set(declared_fields)
    if unknown:
        raise ConfigError(
            f"Unknown configuration for {component.reference}: {', '.join(sorted(unknown))}"
        )
    annotations = get_type_hints(cls)
    validated: dict[str, object] = {}
    try:
        for name, value in component.configuration.items():
            validated[name] = TypeAdapter(annotations[name]).validate_python(value)
        instance = cls(**validated)
    except (KeyError, TypeError, ValidationError) as exc:
        raise ConfigError(f"Invalid configuration for {component.reference}: {exc}") from exc
    return record, instance


def canonical_component(record: RegistryRecord) -> str:
    return f"{record.kind.value}:{record.name}@{record.version}"


def component_alias(component: ComponentUse) -> str:
    name = parse_reference(component.reference).value
    return name.rsplit(".", maxsplit=1)[-1].replace("-", "_")


def apply_dataset_overrides(
    dataset: DatasetSpec,
    pipeline: PipelineSpec,
    overrides: dict[str, JsonValue],
) -> tuple[DatasetSpec, PipelineSpec]:
    source = dataset.source
    stages = list(pipeline.stages)
    sinks = list(dataset.sinks)
    checks = list(dataset.checks)
    metrics = list(dataset.metrics)

    collections: dict[str, list[ComponentUse]] = {
        "stages": stages,
        "sinks": sinks,
        "checks": checks,
        "metrics": metrics,
    }
    for path, value in overrides.items():
        parts = path.split(".")
        if len(parts) < SOURCE_OVERRIDE_PARTS:
            raise ConfigError(
                f"Invalid data override {path!r}; expected source.<field> or "
                "<collection>.<component>.<field>"
            )
        if parts[0] == "source":
            if len(parts) != SOURCE_OVERRIDE_PARTS:
                raise ConfigError(f"Invalid source override path: {path!r}")
            source = _with_configuration(source, parts[1], value)
            continue
        collection = collections.get(parts[0])
        if collection is None or len(parts) != COMPONENT_OVERRIDE_PARTS:
            raise ConfigError(f"Invalid data override path: {path!r}")
        matches = [
            index
            for index, component in enumerate(collection)
            if component_alias(component) == parts[1]
        ]
        if len(matches) != 1:
            raise ConfigError(
                f"Override component {parts[1]!r} in {parts[0]} matched {len(matches)} entries"
            )
        index = matches[0]
        collection[index] = _with_configuration(collection[index], parts[2], value)

    return replace(
        dataset,
        source=source,
        sinks=tuple(sinks),
        checks=tuple(checks),
        metrics=tuple(metrics),
    ), replace(pipeline, stages=tuple(stages))


def validate_component_configuration(
    registry: Registry,
    component: ComponentUse,
    *,
    expected: tuple[EntryKind, ...],
) -> None:
    instantiate_component(registry, component, expected=expected)


def component_configuration(component: ComponentUse) -> dict[str, JsonValue]:
    return dict(component.configuration)


def _with_configuration(
    component: ComponentUse,
    field_name: str,
    value: JsonValue,
) -> ComponentUse:
    return replace(
        component,
        configuration={**component.configuration, field_name: value},
    )
