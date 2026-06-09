from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.data.context import DataContext
from rlab.data.ids import CheckId, DatasetId, MetricId, SourceId, StageId
from rlab.data.recipe import (
    CheckResult,
    DataFlow,
    DatasetRecipe,
    DataSink,
    DataStage,
    FunctionCheck,
    FunctionMetric,
    FunctionSource,
    FunctionStage,
)
from rlab.data.sinks import JsonlSink
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.typing import JsonValue

SourceFn = TypeVar("SourceFn", bound=Callable[[DataContext], Iterable[Any]])
CheckFn = Callable[[Sequence[Any], DataContext], CheckResult]
MetricFn = Callable[[Sequence[Any], DataContext], JsonValue]
StageFn = Callable[[Iterable[Any], DataContext], Iterable[Any]]


def dataset(  # noqa: PLR0913
    name: str,
    *,
    stages: tuple[StageFn | DataStage[Any, Any], ...] = (),
    sinks: tuple[DataSink[Any], ...] | None = None,
    checks: tuple[CheckFn, ...] = (),
    metrics: tuple[MetricFn, ...] = (),
    version: str = "1",
    description: str = "",
    tags: tuple[str, ...] = (),
) -> Callable[[SourceFn], SourceFn]:
    """Declare a dataset recipe and register it from its source function.

    The decorated function is the source. Its name becomes the source ID in the
    manifest. Stage, check, and metric IDs are derived from their function names.
    Lambdas are rejected — define named functions so manifests stay readable.
    """

    def decorate(source_fn: SourceFn) -> SourceFn:
        _require_named(source_fn)
        source = FunctionSource(SourceId(source_fn.__name__), source_fn)

        flow: DataFlow[Any] = DataFlow.from_source(source)
        for stage in stages:
            if hasattr(stage, "apply"):
                flow = flow.then(stage)  # type: ignore[arg-type]
            else:
                _require_named(stage)
                flow = flow.then(FunctionStage(StageId(stage.__name__), stage))

        recipe: DatasetRecipe[Any] = DatasetRecipe(
            id=DatasetId(name),
            flow=flow,
            sinks=sinks if sinks is not None else (JsonlSink(),),
            checks=tuple(_wrap_check(fn) for fn in checks),
            metrics=tuple(_wrap_metric(fn) for fn in metrics),
            version=version,
            description=description,
            tags=tags,
        )

        def _provide() -> DatasetRecipe[Any]:
            return recipe

        _provide.__name__ = name.replace(".", "_").replace("-", "_")
        _provide.__doc__ = description

        register(current_registry(), EntryKind.DATASET, name, _provide, tags=tags)
        return source_fn

    return decorate


def _wrap_check(fn: CheckFn) -> FunctionCheck[Any]:
    _require_named(fn)
    return FunctionCheck(CheckId(fn.__name__), fn)


def _wrap_metric(fn: MetricFn) -> FunctionMetric[Any]:
    _require_named(fn)
    return FunctionMetric(MetricId(fn.__name__), fn)


def _require_named(fn: Callable[..., Any]) -> None:
    if getattr(fn, "__name__", None) == "<lambda>":
        raise ValueError(
            "lambdas are not allowed in @dataset; define a named function "
            "so manifest IDs stay stable and readable"
        )
