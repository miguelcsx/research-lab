from __future__ import annotations

from collections.abc import Callable
from dataclasses import is_dataclass
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.data.model import AuditPolicy, ComponentUse, DatasetSpec, PipelineSpec
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.registry.validation import validate_version

T = TypeVar("T", bound=type[Any])


def _component(kind: EntryKind, name: str, version: str, tags: tuple[str, ...]) -> Callable[[T], T]:
    def decorate(cls: T) -> T:
        if not is_dataclass(cls):
            raise TypeError(f"@{kind.value} requires a dataclass")
        return register(
            current_registry(),
            kind,
            name,
            cls,
            version=version,
            tags=tags,
            declared_by=cls,
        )

    return decorate


def source(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.SOURCE, name, version, tags)


def transform(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.TRANSFORM, name, version, tags)


def filter(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.FILTER, name, version, tags)


def group(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.GROUP, name, version, tags)


def dedup(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.DEDUP, name, version, tags)


def sink(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.SINK, name, version, tags)


def check(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.CHECK, name, version, tags)


def metric(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.METRIC, name, version, tags)


def patterns(
    name: str, *, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _component(EntryKind.PATTERNS, name, version, tags)


def pipeline(
    name: str,
    *,
    stages: tuple[ComponentUse, ...],
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
) -> Callable[[T], T]:
    validate_version(version)

    def decorate(cls: T) -> T:
        spec = PipelineSpec(
            name=name,
            version=version,
            stages=stages,
            description=cls.__doc__ or "",
            tags=tags,
        )
        register(
            current_registry(),
            EntryKind.PIPELINE,
            name,
            spec,
            version=version,
            tags=tags,
            declared_by=cls,
        )
        return cls

    return decorate


def dataset(  # noqa: PLR0913
    name: str,
    *,
    source: ComponentUse,
    pipeline: str,
    sinks: tuple[ComponentUse, ...],
    checks: tuple[ComponentUse, ...] = (),
    metrics: tuple[ComponentUse, ...] = (),
    audit: AuditPolicy | None = None,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    description: str = "",
) -> Callable[[T], T]:
    validate_version(version)
    if not sinks:
        raise ValueError("dataset requires at least one sink")

    def decorate(cls: T) -> T:
        if not isinstance(cls, type):
            raise TypeError("@dataset is class-only")
        dataset_spec = DatasetSpec(
            name=name,
            version=version,
            source=source,
            pipeline=pipeline,
            sinks=sinks,
            checks=checks,
            metrics=metrics,
            audit=audit or AuditPolicy(),
            description=description or cls.__doc__ or "",
            tags=tags,
        )
        register(
            current_registry(),
            EntryKind.DATASET,
            name,
            dataset_spec,
            version=version,
            tags=tags,
            declared_by=cls,
        )
        return cls

    return decorate
