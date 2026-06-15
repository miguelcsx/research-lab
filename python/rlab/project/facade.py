"""Thin Project facade over the Rust registry core."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TypeVar, cast

from rlab._decorators import decorator_factory
from rlab._rlab import ProjectCore
from rlab._typing import JsonObject
from rlab.components import ComponentSpec, Requirements

from .components import (
    build_parts,
    component_identity,
    component_metadata,
    schema_dict,
    validate_model_schema,
)
from .constants import (
    DEFAULT_VERSION,
    ERROR_COMPONENT_NOT_CALLABLE,
    ERROR_COMPONENT_PARAMS_MAPPING,
    KEY_DESCRIPTION,
    KEY_EXPERIMENT_TYPE,
    KEY_PARAMS_SCHEMA,
    KEY_SPEC,
    KEY_STAGES,
    KEY_STEP,
    KEY_STEPS,
    KEY_TAGS,
    KEY_TARGET,
    KEY_TASK,
    KEY_SUITE,
    KEY_VERSION,
    KIND_BENCHMARK,
    KIND_COMPONENT_EXTERNAL_EVALUATION,
    KIND_DATASET,
    KIND_DATASET_SINK,
    KIND_DATASET_SOURCE,
    KIND_EVALUATION,
    KIND_EXPERIMENT,
    KIND_PIPELINE,
    KIND_STUDY,
    KIND_WORKFLOW,
)
from .registry import default_project_name, pinned_or_registered_project
from .registry_helpers import dataset_sinks
from .schemas import signature_schema, validate_signature_params
from .sentinels import SentinelCallable, declaration_sentinel, object_origin, strict_unstable_declaration
from .serde import first_doc_line, jsonable_mapping, jsonable_spec, string_list

T = TypeVar("T")


class Project:
    """Python decorator ergonomics backed by Rust-owned registry state."""

    def __new__(
        cls,
        name: str | None = None,
        root: str | Path | None = None,
    ) -> "Project":
        del root
        return pinned_or_registered_project(cls, name)

    def __init__(self, name: str | None = None, root: str | Path | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.name = name or default_project_name()
        self.root = Path(root) if root is not None else Path.cwd()
        self._core = ProjectCore(self.name, self.root)
        self._initialized = True

    @property
    def records(self) -> list[JsonObject]:
        return cast(list[JsonObject], json.loads(self._core.records_json()))

    def resolve(self, kind: str, name: str) -> object:
        return self._core.resolve(kind, name)

    def record(self, kind: str, name: str) -> JsonObject:
        return cast(JsonObject, json.loads(self._core.record_json(kind, name)))

    def experiment(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator(KIND_EXPERIMENT, name, metadata)

    def declare(
        self,
        kind: str,
        name: str,
        *,
        run: object | None = None,
        **metadata: object,
    ) -> str:
        self._register(
            kind=kind,
            name=name,
            obj=run if run is not None else declaration_sentinel(name),
            metadata=metadata,
        )
        return name

    def sweep(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("sweep", name, metadata)

    def ablation(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("ablation", name, metadata)

    def submission(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("submission", name, metadata)

    def study(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator(KIND_STUDY, name, metadata)

    def study_from_spec(self, name: str, spec: object) -> Callable[[T], T]:
        return self._decorator(KIND_STUDY, name, {KEY_SPEC: jsonable_spec(spec)})

    def experiment_from_spec(self, name: str, spec: object) -> Callable[[T], T]:
        return self._decorator(KIND_EXPERIMENT, name, {KEY_SPEC: jsonable_spec(spec)})

    def external_evaluation(self, name: str, **metadata: object) -> Callable[[T], T]:
        def decorate(obj: T | None = None) -> T:
            target = obj if obj is not None else SentinelCallable(name)
            self._register(
                kind=KIND_COMPONENT_EXTERNAL_EVALUATION,
                name=name,
                obj=target,
                metadata=metadata,
            )
            return cast(T, target)

        return decorate

    def adapter(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("adapter", name, metadata)

    def source(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("source", name, metadata)

    def transform(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("transform", name, metadata)

    def filter(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("filter", name, metadata)

    def group(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("group", name, metadata)

    def dedup(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("dedup", name, metadata)

    def sink(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("sink", name, metadata)

    def check(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("check", name, metadata)

    def metric(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("metric", name, metadata)

    def loader(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("loader", name, metadata)

    def pipeline(
        self,
        name: str,
        *stages: object,
        version: str = DEFAULT_VERSION,
        tags: list[str] | tuple[str, ...] = (),
        description: str | None = None,
    ) -> str:
        self._declare_data(
            KIND_PIPELINE,
            name,
            {
                KEY_STAGES: [jsonable_spec(stage) for stage in stages],
                KEY_VERSION: version,
                KEY_TAGS: list(tags),
                KEY_DESCRIPTION: description,
            },
        )
        return name

    def dataset(self, name: str, **metadata: object) -> str:
        metadata = self._dataset_metadata(name, metadata)
        self._declare_data(KIND_DATASET, name, metadata)
        self._bind_dataset_callables(name, metadata)
        return name

    def define_workflow(self, name: str, *, steps: Iterable[object]) -> object:
        return self._declare_data(
            KIND_WORKFLOW,
            name,
            {KEY_STEPS: [jsonable_spec(step) for step in steps]},
        )

    def component(
        self,
        reference: str | None = None,
        *,
        kind: str | None = None,
        name: str | None = None,
        params_schema: type[object] | None = None,
        requires: Requirements = Requirements(),
        **metadata: object,
    ) -> Callable[[T], T]:
        component_kind, component_name = component_identity(reference, kind, name)
        values = component_metadata(component_kind, component_name, requires, metadata)
        schema: object | None = params_schema

        if params_schema is not None:
            values[KEY_PARAMS_SCHEMA] = schema_dict(
                params_schema,
                f"params schema for {component_kind}:{component_name}",
            )

        def register(obj: T) -> T:
            nonlocal schema
            if params_schema is None:
                values[KEY_PARAMS_SCHEMA] = signature_schema(obj)
                schema = None

            result = self._decorator(component_kind, component_name, values)(obj)
            self._core.set_component_extras(
                component_kind,
                component_name,
                schema,
                json.dumps(requires.to_dict(), sort_keys=True),
            )
            return result

        return register

    def build(
        self,
        reference: str,
        spec: ComponentSpec[object] | Mapping[str, object] | None = None,
        *inject: object,
        **legacy_kwargs: object,
    ) -> object:
        kind, name, params = build_parts(reference, spec)
        factory = self.resolve(kind, name)

        if not callable(factory):
            raise TypeError(ERROR_COMPONENT_NOT_CALLABLE.format(kind=kind, name=name))

        schema = self._core.schema(kind, name)
        if schema is not None:
            return cast(Callable[..., object], factory)(
                *inject,
                validate_model_schema(cast(type[object], schema), params, kind, name),
                **legacy_kwargs,
            )

        if not isinstance(params, Mapping):
            raise TypeError(ERROR_COMPONENT_PARAMS_MAPPING.format(kind=kind, name=name))

        return cast(Callable[..., object], factory)(
            *inject,
            **validate_signature_params(factory, params),
            **legacy_kwargs,
        )

    def requirements(self, kind: str, name: str) -> Requirements:
        value = self._core.requirements_json(kind, name)
        if value is None:
            return Requirements()
        data = json.loads(value)
        return Requirements(
            model_outputs=tuple(data.get("model_outputs", ())),
            model_heads=tuple(data.get("model_heads", ())),
            batch_fields=tuple(data.get("batch_fields", ())),
            capabilities=tuple(data.get("capabilities", ())),
            artifacts=tuple(data.get("artifacts", ())),
        )

    def benchmark(
        self, name: str, *, target: str, **metadata: object
    ) -> Callable[[T], T]:
        return self._decorator(KIND_BENCHMARK, name, {**metadata, KEY_TARGET: target})

    def workflow(self, name: str, *, step: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator(KIND_WORKFLOW, name, {**metadata, KEY_STEP: step})

    def evaluation(self, suite: str, task: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator(
            KIND_EVALUATION,
            f"{suite}.{task}",
            {**metadata, KEY_SUITE: suite, KEY_TASK: task},
        )

    def result_schema(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._decorator("result_schema", name, metadata)

    def _decorator(
        self,
        kind: str,
        name: str,
        metadata: Mapping[str, object],
    ) -> Callable[[T], T]:
        return decorator_factory(self, kind, name, dict(metadata))

    def _planned_experiment(
        self,
        experiment_type: str,
        name: str,
        metadata: dict[str, object],
    ) -> Callable[[T], T]:
        return self._decorator(
            KIND_EXPERIMENT,
            name,
            {**metadata, KEY_EXPERIMENT_TYPE: experiment_type},
        )

    def _declare_data(
        self,
        kind: str,
        name: str,
        metadata: Mapping[str, object],
    ) -> object:
        sentinel = declaration_sentinel(name)
        self._register(kind=kind, name=name, obj=sentinel, metadata=dict(metadata))
        return sentinel

    def _bind_dataset_callables(
        self,
        name: str,
        metadata: Mapping[str, object],
    ) -> None:
        source = metadata.get("_source_callable")
        if source is not None:
            self._core.bind_callable(KIND_DATASET_SOURCE, name, source)

        sink_callables = metadata.get("_sink_callables", ())
        if not isinstance(sink_callables, list):
            sink_callables = []
        for index, sink in enumerate(sink_callables):
            self._core.bind_callable(KIND_DATASET_SINK, f"{name}:{index}", sink)

    def _dataset_metadata(
        self,
        name: str,
        metadata: Mapping[str, object],
    ) -> dict[str, object]:
        values = dict(metadata)
        source = values.get("source")
        if source is not None and not isinstance(source, str):
            values["_source_callable"] = source
            values["source"] = f"{KIND_DATASET_SOURCE}:{name}"

        sink_callables = [
            sink for sink in dataset_sinks(values) if sink is not None and not isinstance(sink, str)
        ]
        if sink_callables:
            values["_sink_callables"] = sink_callables
            values["sinks"] = [
                f"{KIND_DATASET_SINK}:{name}:{index}"
                for index, _ in enumerate(sink_callables)
            ]
        return values

    def _register(
        self,
        *,
        kind: str,
        name: str,
        obj: object,
        metadata: dict[str, object],
    ) -> None:
        module, qualname, source = object_origin(obj)
        if strict_unstable_declaration(obj=obj, qualname=qualname, source=source):
            raise ValueError(f"unstable strict declaration: {kind}:{name}")

        metadata_copy = jsonable_mapping(
            {
                key: value
                for key, value in metadata.items()
                if not key.startswith("_")
            },
            f"metadata for {kind}:{name}",
        )
        version = str(metadata_copy.pop(KEY_VERSION, DEFAULT_VERSION))
        tags = string_list(metadata_copy.pop(KEY_TAGS, []), KEY_TAGS)
        self._core.register(
            kind,
            name,
            module,
            qualname,
            Path(source),
            first_doc_line(obj),
            json.dumps(metadata_copy, sort_keys=True),
            obj,
            version,
            tags,
        )
