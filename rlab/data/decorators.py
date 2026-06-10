from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.data.model import AuditPolicy, ComponentMeta, ComponentUse, DatasetSpec, PipelineSpec
from rlab.registry.decorators import register
from rlab.registry.namespaces import validate_name
from rlab.registry.store import Registry
from rlab.registry.validation import validate_version
from rlab.typing import JsonValue

T = TypeVar("T", bound=type[Any])


def _serialize_value(value: object) -> JsonValue:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")  # type: ignore[union-attr]
    if is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)  # type: ignore[arg-type]
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    return value  # type: ignore[return-value]


def _non_default_config(instance: object) -> dict[str, JsonValue]:
    if not is_dataclass(instance) or isinstance(instance, type):
        return {}
    config: dict[str, JsonValue] = {}
    for f in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, f.name)
        if f.default is not dataclasses.MISSING and value == f.default:
            continue
        if f.default_factory is not dataclasses.MISSING and value == f.default_factory():  # type: ignore[misc]
            continue
        config[f.name] = _serialize_value(value)
    return config


def _to_component_use(obj: type | object) -> ComponentUse:
    cls = obj if isinstance(obj, type) else type(obj)
    meta: ComponentMeta | None = getattr(cls, "_rlab_meta", None)
    if meta is None:
        raise TypeError(f"{cls.__name__} is not an rlab-decorated component (missing _rlab_meta)")
    ref = f"{meta.kind}:{meta.name}"
    if isinstance(obj, type):
        return ComponentUse(ref, {})
    return ComponentUse(ref, _non_default_config(obj))


def _component(
    kind: EntryKind,
    name: str,
    version: str,
    tags: tuple[str, ...],
    registry: Registry,
) -> Callable[[T], T]:
    def decorate(cls: T) -> T:
        if not is_dataclass(cls):
            raise TypeError(f"@{kind.value} requires a dataclass")
        cls._rlab_meta = ComponentMeta(kind=kind.value, name=name)  # type: ignore[attr-defined]
        return register(
            registry,
            kind,
            name,
            cls,
            version=version,
            tags=tags,
            declared_by=cls,
        )

    return decorate


def source(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.SOURCE, name, version, tags, registry)


def transform(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.TRANSFORM, name, version, tags, registry)


def filter(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.FILTER, name, version, tags, registry)


def group(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.GROUP, name, version, tags, registry)


def dedup(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.DEDUP, name, version, tags, registry)


def sink(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.SINK, name, version, tags, registry)


def check(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.CHECK, name, version, tags, registry)


def metric(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.METRIC, name, version, tags, registry)


def patterns(
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    return _component(EntryKind.PATTERNS, name, version, tags, registry)


def component(
    kind: str,
    name: str,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    """Register a user-defined component (tokenizer, model, solver, ...).

    Stored as ``EntryKind.COMPONENT`` with the qualified name ``"{kind}:{name}"``;
    the ``target_kind`` field records the kind so benchmarks can match it.
    """
    validate_version(version)
    validate_name(f"{kind}:{name}")

    def decorate(cls: T) -> T:
        cls._rlab_meta = ComponentMeta(kind=EntryKind.COMPONENT.value, name=f"{kind}:{name}")  # type: ignore[attr-defined]
        return register(
            registry,
            EntryKind.COMPONENT,
            f"{kind}:{name}",
            cls,
            version=version,
            target_kind=kind,
            tags=tags,
            declared_by=cls,
        )

    return decorate


def benchmark(
    name: str,
    *,
    target: str,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[T], T]:
    """Register a benchmark that runs against a target of the given kind.

    Targets are user-defined components (tokenizer, model, ...).
    """
    validate_version(version)
    validate_name(name)

    def decorate(fn: T) -> T:
        return register(
            registry,
            EntryKind.BENCHMARK,
            name,
            fn,
            version=version,
            target_kind=target,
            tags=tags,
            declared_by=fn,
        )

    return decorate


def _resolve_stage(stage: type | object) -> ComponentUse:
    if isinstance(stage, ComponentUse):
        return stage
    return _to_component_use(stage)


def pipeline(
    name: str,
    *stages: type | object | ComponentUse,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    description: str = "",
    registry: Registry,
) -> PipelineSpec:
    validate_version(version)
    resolved = tuple(_resolve_stage(s) for s in stages)
    spec = PipelineSpec(
        name=name,
        version=version,
        stages=resolved,
        description=description,
        tags=tags,
    )
    register(
        registry,
        EntryKind.PIPELINE,
        name,
        spec,
        version=version,
        tags=tags,
    )
    return spec


def dataset(  # noqa: PLR0913
    name: str,
    *,
    source: type | object | ComponentUse,
    pipeline: str | PipelineSpec,
    sinks: tuple[type | object | ComponentUse, ...] = (),
    checks: tuple[type | object | ComponentUse, ...] = (),
    metrics: tuple[type | object | ComponentUse, ...] = (),
    audit: AuditPolicy | None = None,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    description: str = "",
    registry: Registry,
) -> DatasetSpec:
    validate_version(version)
    if not sinks:
        raise ValueError("dataset requires at least one sink")

    pipeline_ref = f"pipeline:{pipeline.name}" if isinstance(pipeline, PipelineSpec) else pipeline

    dataset_spec = DatasetSpec(
        name=name,
        version=version,
        source=_resolve_stage(source),
        pipeline=pipeline_ref,
        sinks=tuple(_resolve_stage(s) for s in sinks),
        checks=tuple(_resolve_stage(c) for c in checks),
        metrics=tuple(_resolve_stage(m) for m in metrics),
        audit=audit or AuditPolicy(),
        description=description,
        tags=tags,
    )
    register(
        registry,
        EntryKind.DATASET,
        name,
        dataset_spec,
        version=version,
        tags=tags,
    )
    return dataset_spec
