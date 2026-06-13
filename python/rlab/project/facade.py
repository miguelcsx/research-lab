"""Project facade and declaration registration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TypeVar, cast

from rlab._decorators import decorator_factory
from rlab._typing import JsonObject, JsonValue
from rlab.components import ComponentSpec, Requirements

from .components import (
    build_parts,
    component_identity,
    component_metadata,
    schema_dict,
    validate_model_schema,
)
from .constants import *
from .registry import default_project_name, pinned_or_registered_project
from .registry_helpers import (
    dataset_sinks,
    step_name,
    validate_identifier,
    workflow_step_metadata,
    workflow_steps,
)
from .schemas import signature_schema, validate_signature_params
from .sentinels import (
    SentinelCallable,
    WorkflowCallable,
    declaration_sentinel,
    object_origin,
    strict_unstable_declaration,
)
from .serde import (
    first_doc_line,
    jsonable_mapping,
    jsonable_spec,
    relative_source,
    string_list,
)

T = TypeVar("T")


class Project:
    """Python facade for rlab project declarations.

    ``Project()`` is zero-config friendly. During runner imports the active
    project is pinned, so declarations register into the Rust CLI request's
    project even if user modules construct their own ``Project()`` instance.
    """

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
        self._records: list[JsonObject] = []
        self._record_index: dict[tuple[str, str], JsonObject] = {}
        self._callables: dict[tuple[str, str], object] = {}
        self._component_schemas: dict[tuple[str, str], type[object]] = {}
        self._component_requirements: dict[tuple[str, str], Requirements] = {}
        self._initialized = True

    @property
    def records(self) -> list[JsonObject]:
        """Return declarative registry records collected in this process."""
        return list(self._records)

    def resolve(self, kind: str, name: str) -> object:
        """Resolve a process-local callable by kind/name."""
        key = (kind, name)
        if key not in self._callables:
            raise KeyError(ERROR_NO_CALLABLE.format(kind=kind, name=name))
        return self._callables[key]

    def record(self, kind: str, name: str) -> JsonObject:
        """Return the declarative registry record for a kind/name pair."""
        record = self._find_record(kind, name)
        if record is None:
            raise KeyError(ERROR_NO_RECORD.format(kind=kind, name=name))
        return dict(record)

    def experiment(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a Python experiment callable."""
        return self._decorator(KIND_EXPERIMENT, name, metadata)

    def declare(
        self,
        kind: str,
        name: str,
        *,
        run: object | None = None,
        **metadata: object,
    ) -> str:
        """Register a declaration represented primarily as data."""
        self._register(
            kind=kind,
            name=name,
            obj=run if run is not None else declaration_sentinel(name),
            metadata=metadata,
        )
        return name

    def sweep(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a sweep using the standard experiment planner."""
        return self._planned_experiment("sweep", name, metadata)

    def ablation(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a controlled ablation using the experiment planner."""
        return self._planned_experiment("ablation", name, metadata)

    def submission(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a submission run using the experiment planner."""
        return self._planned_experiment("submission", name, metadata)

    def study(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a study declaration."""
        return self._decorator(KIND_STUDY, name, metadata)

    def study_from_spec(self, name: str, spec: object) -> Callable[[T], T]:
        """Register a study from a reusable spec object."""
        return self._decorator(KIND_STUDY, name, {KEY_SPEC: jsonable_spec(spec)})

    def experiment_from_spec(self, name: str, spec: object) -> Callable[[T], T]:
        """Register an experiment from a reusable spec object."""
        return self._decorator(KIND_EXPERIMENT, name, {KEY_SPEC: jsonable_spec(spec)})

    def external_evaluation(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register an external-command evaluation declaration."""

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
        """Register an adapter class."""
        return self._decorator("adapter", name, metadata)

    def source(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a dataset source class or callable."""
        return self._decorator("source", name, metadata)

    def transform(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a record-level transform class or callable."""
        return self._decorator("transform", name, metadata)

    def filter(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a record-level filter class or callable."""
        return self._decorator("filter", name, metadata)

    def group(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a batch-level grouping stage."""
        return self._decorator("group", name, metadata)

    def dedup(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a batch-level deduplication stage."""
        return self._decorator("dedup", name, metadata)

    def sink(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a dataset sink."""
        return self._decorator("sink", name, metadata)

    def check(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a dataset check."""
        return self._decorator("check", name, metadata)

    def metric(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a dataset metric."""
        return self._decorator("metric", name, metadata)

    def loader(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a loader — a component that resolves external paths.

        A loader is a class that exposes ``load(path)`` and is invoked
        when a target reference has the form ``<kind>:<loader>:<path>``.
        Loaders are how projects integrate external resources (model
        registries, artifact stores, dataset hubs) without rlab needing
        vendor-specific code.
        """
        return self._decorator("loader", name, metadata)

    def pipeline(
        self,
        name: str,
        *stages: object,
        version: str = DEFAULT_VERSION,
        tags: list[str] | tuple[str, ...] = (),
        description: str | None = None,
    ) -> str:
        """Register a pipeline declaration."""
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
        """Register a dataset declaration."""
        self._declare_data(KIND_DATASET, name, metadata)
        self._bind_dataset_callables(name, metadata)
        return name

    def define_workflow(self, name: str, *, steps: Iterable[object]) -> object:
        """Register a workflow assembled imperatively from step descriptors."""
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
        """Register a component and infer public params from keyword-only args."""
        component_kind, component_name = component_identity(reference, kind, name)
        key = (component_kind, component_name)
        values = component_metadata(component_kind, component_name, requires, metadata)

        if params_schema is not None:
            values[KEY_PARAMS_SCHEMA] = schema_dict(
                params_schema,
                f"params schema for {component_kind}:{component_name}",
            )

        def register(obj: T) -> T:
            if params_schema is None:
                values[KEY_PARAMS_SCHEMA] = signature_schema(obj)

            result = self._decorator(component_kind, component_name, values)(obj)

            if params_schema is not None:
                self._component_schemas[key] = params_schema

            self._component_requirements[key] = requires
            self._callables[key] = obj
            return result

        return register

    def build(
        self,
        reference: str,
        spec: ComponentSpec[object] | Mapping[str, object] | None = None,
        *inject: object,
        **legacy_kwargs: object,
    ) -> object:
        """Resolve, validate, and instantiate a component by namespaced reference."""
        kind, name, params = build_parts(reference, spec)
        factory = self.resolve(kind, name)

        if not callable(factory):
            raise TypeError(ERROR_COMPONENT_NOT_CALLABLE.format(kind=kind, name=name))

        schema = self._component_schemas.get((kind, name))
        if schema is not None:
            validated = validate_model_schema(schema, params, kind, name)
            return cast(Callable[..., object], factory)(
                *inject, validated, **legacy_kwargs
            )

        if not isinstance(params, Mapping):
            raise TypeError(ERROR_COMPONENT_PARAMS_MAPPING.format(kind=kind, name=name))

        return cast(Callable[..., object], factory)(
            *inject,
            **validate_signature_params(factory, params),
            **legacy_kwargs,
        )

    def requirements(self, kind: str, name: str) -> Requirements:
        """Return requirements declared by a component."""
        return self._component_requirements.get((kind, name), Requirements())

    def benchmark(
        self, name: str, *, target: str, **metadata: object
    ) -> Callable[[T], T]:
        """Register a benchmark callable."""
        return self._decorator(KIND_BENCHMARK, name, {**metadata, KEY_TARGET: target})

    def workflow(self, name: str, *, step: str, **metadata: object) -> Callable[[T], T]:
        """Register a workflow step callable."""
        return self._decorator(KIND_WORKFLOW, name, {**metadata, KEY_STEP: step})

    def evaluation(self, suite: str, task: str, **metadata: object) -> Callable[[T], T]:
        """Register an evaluation task callable."""
        return self._decorator(
            KIND_EVALUATION,
            f"{suite}.{task}",
            {**metadata, KEY_SUITE: suite, KEY_TASK: task},
        )

    def result_schema(self, name: str, **metadata: object) -> Callable[[T], T]:
        """Register a result schema class."""
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
        source = metadata.get("source")
        if source is not None and not isinstance(source, str):
            self._callables[(KIND_DATASET_SOURCE, name)] = source

        for index, sink in enumerate(dataset_sinks(metadata)):
            if sink is not None and not isinstance(sink, str):
                self._callables[(KIND_DATASET_SINK, f"{name}:{index}")] = sink

    def _register(
        self,
        *,
        kind: str,
        name: str,
        obj: object,
        metadata: dict[str, object],
    ) -> None:
        validate_identifier(kind, name)

        module, qualname, source = object_origin(obj)
        if strict_unstable_declaration(obj=obj, qualname=qualname, source=source):
            raise ValueError(ERROR_UNSTABLE_STRICT.format(kind=kind, name=name))

        metadata_copy = jsonable_mapping(metadata, f"metadata for {kind}:{name}")
        version = str(metadata_copy.pop(KEY_VERSION, DEFAULT_VERSION))
        tags = string_list(metadata_copy.pop(KEY_TAGS, []), KEY_TAGS)
        key = (kind, name)
        step = metadata_copy.get(KEY_STEP)
        record = self._record_payload(
            kind=kind,
            name=name,
            obj=obj,
            module=module,
            qualname=qualname,
            source=source,
            version=version,
            tags=tags,
            metadata=metadata_copy,
        )

        if key in self._callables:
            if kind == KIND_WORKFLOW and isinstance(step, str):
                self._append_workflow_step(name, step, obj, metadata_copy, record)
                return
            raise ValueError(ERROR_DUPLICATE_DECLARATION.format(kind=kind, name=name))

        if kind == KIND_WORKFLOW and isinstance(step, str):
            self._register_first_workflow_step(name, step, obj, metadata_copy, record)
        else:
            self._callables[key] = obj

        self._records.append(record)
        self._record_index[(kind, name)] = record

    def _record_payload(
        self,
        *,
        kind: str,
        name: str,
        obj: object,
        module: str,
        qualname: str,
        source: str,
        version: str,
        tags: list[str],
        metadata: JsonObject,
    ) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: SCHEMA_VERSION,
            KEY_KIND: kind,
            KEY_NAME: name,
            KEY_VERSION: version,
            KEY_MODULE: module,
            KEY_QUALNAME: qualname,
            KEY_SOURCE: relative_source(source, self.root),
            KEY_TAGS: cast(list[JsonValue], tags),
            KEY_DESCRIPTION: first_doc_line(obj),
            KEY_METADATA: metadata,
        }

    def _register_first_workflow_step(
        self,
        workflow_name: str,
        step: str,
        obj: object,
        metadata: JsonObject,
        record: JsonObject,
    ) -> None:
        record[KEY_METADATA] = {
            KEY_STEPS: [workflow_step_metadata(step, record, metadata)]
        }
        self._callables[(KIND_WORKFLOW_STEP, f"{workflow_name}:{step}")] = obj
        self._callables[(KIND_WORKFLOW, workflow_name)] = WorkflowCallable(
            workflow_name
        )

    def _append_workflow_step(
        self,
        workflow_name: str,
        step: str,
        obj: object,
        metadata: JsonObject,
        record: JsonObject,
    ) -> None:
        existing = self._find_record(KIND_WORKFLOW, workflow_name)
        if existing is None:
            raise ValueError(
                ERROR_WORKFLOW_RECORD_MISSING.format(workflow_name=workflow_name)
            )

        steps = workflow_steps(existing, workflow_name)
        if any(step_name(item) == step for item in steps):
            raise ValueError(
                ERROR_DUPLICATE_WORKFLOW_STEP.format(
                    workflow_name=workflow_name,
                    step_name=step,
                )
            )

        steps.append(workflow_step_metadata(step, record, metadata))
        self._callables[(KIND_WORKFLOW_STEP, f"{workflow_name}:{step}")] = obj

    def _find_record(self, kind: str, name: str) -> JsonObject | None:
        return self._record_index.get((kind, name))
