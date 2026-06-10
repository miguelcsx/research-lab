from collections.abc import Callable
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.data.decorators import (
    check,
    dataset,
    dedup,
    filter,
    group,
    metric,
    patterns,
    pipeline,
    sink,
    source,
    transform,
)
from rlab.evaluations.decorators import evaluation
from rlab.experiments.decorators import experiment
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.studies.decorators import study
from rlab.workflows.decorators import workflow

T = TypeVar("T", bound=Callable[..., Any] | type[Any])


def _decorator(
    kind: EntryKind,
    name: str,
    *,
    version: str = "1.0.0",
    target_kind: str | None = None,
    tags: tuple[str, ...] = (),
) -> Callable[[T], T]:
    return lambda value: register(
        current_registry(),
        kind,
        name,
        value,
        version=version,
        target_kind=target_kind,
        tags=tags,
    )


def component(kind: str, name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(
        EntryKind.COMPONENT,
        f"{kind}:{name}",
        version=version,
        target_kind=kind,
    )


def benchmark(
    name: str,
    *,
    target: str,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
) -> Callable[[T], T]:
    return _decorator(
        EntryKind.BENCHMARK,
        name,
        version=version,
        target_kind=target,
        tags=tags,
    )


def adapter(name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(EntryKind.ADAPTER, name, version=version)


def result_schema(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.RESULT_SCHEMA, name)


__all__ = [
    "adapter",
    "benchmark",
    "component",
    "check",
    "dedup",
    "filter",
    "group",
    "metric",
    "pipeline",
    "dataset",
    "sink",
    "source",
    "transform",
    "evaluation",
    "experiment",
    "result_schema",
    "study",
    "patterns",
    "workflow",
]
