from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, cast

from rlab.constants import EntryKind
from rlab.data.context import DataContext
from rlab.data.ids import CheckId, DatasetId, MetricId, OutputId, SourceId, StageId
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.typing import JsonValue

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
RecordT = TypeVar("RecordT")
SourceT_co = TypeVar("SourceT_co", covariant=True)
InputT_contra = TypeVar("InputT_contra", contravariant=True)
OutputT_co = TypeVar("OutputT_co", covariant=True)
RecordT_contra = TypeVar("RecordT_contra", contravariant=True)


class DataSource(Protocol[SourceT_co]):
    @property
    def id(self) -> SourceId: ...

    def read(self, ctx: DataContext) -> Iterable[SourceT_co]: ...


class DataStage(Protocol[InputT_contra, OutputT_co]):
    @property
    def id(self) -> StageId: ...

    def apply(
        self,
        records: Iterable[InputT_contra],
        ctx: DataContext,
    ) -> Iterable[OutputT_co]: ...


class DataCheck(Protocol[RecordT_contra]):
    @property
    def id(self) -> CheckId: ...

    def evaluate(
        self,
        records: Sequence[RecordT_contra],
        ctx: DataContext,
    ) -> CheckResult: ...


class DataMetric(Protocol[RecordT_contra]):
    @property
    def id(self) -> MetricId: ...

    def measure(self, records: Sequence[RecordT_contra], ctx: DataContext) -> JsonValue: ...


class DataSink(Protocol[RecordT_contra]):
    @property
    def id(self) -> OutputId: ...

    def write(self, records: Sequence[RecordT_contra], ctx: DataContext) -> SinkResult: ...


@dataclass(frozen=True, slots=True)
class CheckResult:
    passed: bool
    status: str = "error"
    metrics: Mapping[str, float] = field(default_factory=dict)
    message: str = ""

    @property
    def manifest_status(self) -> str:
        return "passed" if self.passed else self.status


@dataclass(frozen=True, slots=True)
class SinkResult:
    outputs: Mapping[OutputId, Path]
    stats: Mapping[str, JsonValue] = field(default_factory=dict)
    checks: Mapping[str, str] = field(default_factory=dict)
    licenses: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DataFlow(Generic[RecordT]):
    sources: tuple[DataSource[Any], ...]
    stages: tuple[DataStage[Any, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("DataFlow requires at least one source")
        _require_unique("source", (source.id for source in self.sources))
        _require_unique("stage", (stage.id for stage in self.stages))

    @staticmethod
    def from_source(source: DataSource[InputT]) -> DataFlow[InputT]:
        return DataFlow(sources=(source,))

    @staticmethod
    def from_sources(*sources: DataSource[InputT]) -> DataFlow[InputT]:
        if not sources:
            raise ValueError("DataFlow requires at least one source")
        return DataFlow(sources=cast(tuple[DataSource[Any], ...], sources))

    def then(self, stage: DataStage[RecordT, OutputT]) -> DataFlow[OutputT]:
        return DataFlow(sources=self.sources, stages=(*self.stages, stage))


@dataclass(frozen=True, slots=True)
class DatasetRecipe(Generic[RecordT]):
    id: DatasetId
    flow: DataFlow[RecordT]
    sinks: tuple[DataSink[RecordT], ...]
    checks: tuple[DataCheck[RecordT], ...] = ()
    metrics: tuple[DataMetric[RecordT], ...] = ()
    version: str = "1"
    description: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.sinks:
            raise ValueError("DatasetRecipe requires at least one sink")
        _require_unique("source", (source.id for source in self.flow.sources))
        _require_unique("stage", (stage.id for stage in self.flow.stages))
        _require_unique("sink", (sink.id for sink in self.sinks))
        _require_unique("check", (check.id for check in self.checks))
        _require_unique("metric", (metric.id for metric in self.metrics))

    def replace(  # noqa: PLR0913
        self,
        *,
        id: DatasetId | None = None,
        flow: DataFlow[RecordT] | None = None,
        sinks: tuple[DataSink[RecordT], ...] | None = None,
        checks: tuple[DataCheck[RecordT], ...] | None = None,
        metrics: tuple[DataMetric[RecordT], ...] | None = None,
        version: str | None = None,
        description: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> DatasetRecipe[RecordT]:
        return replace(
            self,
            id=id or self.id,
            flow=flow or self.flow,
            sinks=self.sinks if sinks is None else sinks,
            checks=self.checks if checks is None else checks,
            metrics=self.metrics if metrics is None else metrics,
            version=version or self.version,
            description=self.description if description is None else description,
            tags=self.tags if tags is None else tags,
        )


@dataclass(frozen=True, slots=True, init=False)
class DatasetCatalog:
    recipes: tuple[DatasetRecipe[Any], ...]

    def __init__(self, *recipes: DatasetRecipe[Any]) -> None:
        if not recipes:
            raise ValueError("DatasetCatalog requires at least one recipe")
        _require_unique("dataset", (recipe.id for recipe in recipes))
        object.__setattr__(self, "recipes", recipes)


@dataclass(frozen=True, slots=True)
class FunctionSource(Generic[RecordT]):
    id: SourceId
    reader: Callable[[DataContext], Iterable[RecordT]]

    def read(self, ctx: DataContext) -> Iterable[RecordT]:
        return self.reader(ctx)


@dataclass(frozen=True, slots=True)
class FunctionStage(Generic[InputT, OutputT]):
    id: StageId
    transform: Callable[[Iterable[InputT], DataContext], Iterable[OutputT]]

    def apply(self, records: Iterable[InputT], ctx: DataContext) -> Iterable[OutputT]:
        return self.transform(records, ctx)


@dataclass(frozen=True, slots=True)
class FunctionCheck(Generic[RecordT]):
    id: CheckId
    evaluator: Callable[[Sequence[RecordT], DataContext], CheckResult]

    def evaluate(self, records: Sequence[RecordT], ctx: DataContext) -> CheckResult:
        return self.evaluator(records, ctx)


@dataclass(frozen=True, slots=True)
class FunctionMetric(Generic[RecordT]):
    id: MetricId
    measurer: Callable[[Sequence[RecordT], DataContext], JsonValue]

    def measure(self, records: Sequence[RecordT], ctx: DataContext) -> JsonValue:
        return self.measurer(records, ctx)


@dataclass(frozen=True, slots=True)
class FunctionSink(Generic[RecordT]):
    id: OutputId
    writer: Callable[[Sequence[RecordT], DataContext], SinkResult]

    def write(self, records: Sequence[RecordT], ctx: DataContext) -> SinkResult:
        return self.writer(records, ctx)


def register_datasets(catalog: DatasetCatalog) -> DatasetCatalog:
    registry = current_registry()
    for recipe in catalog.recipes:
        register(
            registry,
            EntryKind.DATASET,
            str(recipe.id),
            _provider(recipe),
            tags=recipe.tags,
        )
    return catalog


def _provider(recipe: DatasetRecipe[Any]) -> Callable[[], DatasetRecipe[Any]]:
    def provide() -> DatasetRecipe[Any]:
        return recipe

    provide.__name__ = str(recipe.id).replace(".", "_").replace("-", "_")
    provide.__doc__ = recipe.description
    return provide


def _require_unique(kind: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {kind} id: {value!r}")
        seen.add(value)
