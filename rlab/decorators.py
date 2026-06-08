from collections.abc import Callable
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.registry.context import current_registry
from rlab.registry.decorators import register

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
    name: str, *, target: str, version: str = "1.0.0", tags: tuple[str, ...] = ()
) -> Callable[[T], T]:
    return _decorator(
        EntryKind.BENCHMARK,
        name,
        version=version,
        target_kind=target,
        tags=tags,
    )


def suite(name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(EntryKind.SUITE, name, version=version)


def external_suite(name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(EntryKind.EXTERNAL_SUITE, name, version=version)


def experiment(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.EXPERIMENT, name)


def baseline(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.BASELINE, name)


def workflow(name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(EntryKind.WORKFLOW, name, version=version)


def workflow_step(name: str, *, version: str = "1.0.0") -> Callable[[T], T]:
    return _decorator(EntryKind.WORKFLOW_STEP, name, version=version)


def result_schema(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.RESULT_SCHEMA, name)


def data_source(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_SOURCE, name)


def data_transform(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_TRANSFORM, name)


def data_check(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_CHECK, name)


def data_metric(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_METRIC, name)


def dataset_variant(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATASET, name)


def data_experiment(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_EXPERIMENT, name)


def data_ablation(name: str) -> Callable[[T], T]:
    return _decorator(EntryKind.DATA_ABLATION, name)
