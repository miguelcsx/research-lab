"""Thin runtime decorator facade over the Rust registry core."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TypeVar, cast

from rlab._decorators import decorator_factory
from rlab._rlab import ProjectCore
from rlab._typing import JsonObject

from .constants import (
    DEFAULT_VERSION,
    KEY_ADAPTER,
    KEY_AXES,
    KEY_EXPERIMENT_TYPE,
    KEY_PARAM_SCHEMA,
    KEY_PARAMS,
    KEY_SEEDS,
    KEY_STEPS,
    KEY_TAGS,
    KEY_TARGET,
    KEY_TARGETS,
    KEY_VERSION,
    KIND_ADAPTER,
    KIND_BENCHMARK,
    KIND_EVALUATION,
    KIND_EXECUTOR,
    KIND_EXPERIMENT,
    KIND_EXPORTER,
    KIND_LOADER,
    KIND_NOTIFIER,
    KIND_REPORTER,
    KIND_RESOLVER,
    KIND_STUDY,
    KIND_WORKFLOW,
)
from .registry import default_project_name, pinned_or_registered_project
from .sentinels import object_origin, strict_unstable_declaration
from .serde import first_doc_line, jsonable_mapping, jsonable_spec, string_list

T = TypeVar("T")


class Project:
    """Runtime entry decorator facade backed by Rust-owned registry state."""

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

    def experiment(
        self,
        name: str,
        *,
        params: object | None = None,
        **metadata: object,
    ) -> Callable[[T], T]:
        return self._runtime_decorator(KIND_EXPERIMENT, name, params=params, metadata=metadata)

    def sweep(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("sweep", name, metadata)

    def ablation(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("ablation", name, metadata)

    def submission(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._planned_experiment("submission", name, metadata)

    def study(
        self,
        name: str,
        *,
        targets: Iterable[object] = (),
        params: object | None = None,
        axes: object | None = None,
        seeds: Iterable[object] = (),
        **metadata: object,
    ) -> Callable[[T], T]:
        values = dict(metadata)
        if targets:
            values[KEY_TARGETS] = [jsonable_spec(target) for target in targets]
        if params is not None:
            values[KEY_PARAMS] = jsonable_spec(params)
        if axes is not None:
            values[KEY_AXES] = jsonable_spec(axes)
        if seeds:
            values[KEY_SEEDS] = [jsonable_spec(seed) for seed in seeds]
        return self._runtime_decorator(KIND_STUDY, name, metadata=values)

    def workflow(
        self,
        name: str,
        *,
        steps: Iterable[object] = (),
        **metadata: object,
    ) -> Callable[[T], T]:
        values = dict(metadata)
        if steps:
            values[KEY_STEPS] = [jsonable_spec(step) for step in steps]
        return self._runtime_decorator(KIND_WORKFLOW, name, metadata=values)

    def benchmark(
        self,
        name: str,
        *,
        target: object | None = None,
        params: object | None = None,
        **metadata: object,
    ) -> Callable[[T], T]:
        values = dict(metadata)
        if target is not None:
            values[KEY_TARGET] = jsonable_spec(target)
        return self._runtime_decorator(KIND_BENCHMARK, name, params=params, metadata=values)

    def evaluation(
        self,
        name: str,
        *,
        params: object | None = None,
        adapter: str | None = None,
        **metadata: object,
    ) -> Callable[[T], T]:
        values = dict(metadata)
        if adapter is not None:
            values[KEY_ADAPTER] = adapter
        return self._runtime_decorator(KIND_EVALUATION, name, params=params, metadata=values)

    def adapter(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_ADAPTER, name, metadata)

    def loader(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_LOADER, name, metadata)

    def executor(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_EXECUTOR, name, metadata)

    def resolver(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_RESOLVER, name, metadata)

    def exporter(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_EXPORTER, name, metadata)

    def reporter(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_REPORTER, name, metadata)

    def notifier(self, name: str, **metadata: object) -> Callable[[T], T]:
        return self._support_decorator(KIND_NOTIFIER, name, metadata)

    def _planned_experiment(
        self,
        experiment_type: str,
        name: str,
        metadata: dict[str, object],
    ) -> Callable[[T], T]:
        return self._runtime_decorator(
            KIND_EXPERIMENT,
            name,
            metadata={**metadata, KEY_EXPERIMENT_TYPE: experiment_type},
        )

    def _support_decorator(
        self,
        kind: str,
        name: str,
        metadata: Mapping[str, object],
    ) -> Callable[[T], T]:
        return self._runtime_decorator(kind, name, metadata=metadata)

    def _runtime_decorator(
        self,
        kind: str,
        name: str,
        *,
        params: object | None = None,
        metadata: Mapping[str, object],
    ) -> Callable[[T], T]:
        values = dict(metadata)
        param_type = _params_type(kind, name, params)
        if param_type is not None:
            values[KEY_PARAM_SCHEMA] = schema_dict(param_type, f"params for {kind}:{name}")
        elif params is not None:
            values[KEY_PARAMS] = jsonable_spec(params)

        def register(obj: T) -> T:
            result = decorator_factory(self, kind, name, values)(obj)
            if param_type is not None:
                self._core.set_params_type(kind, name, param_type)
            return result

        return register

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
            {key: value for key, value in metadata.items() if not key.startswith("_")},
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


def _params_type(kind: str, name: str, params: object | None) -> type[object] | None:
    del kind, name
    return params if isinstance(params, type) else None


def schema_dict(param_type: type[object], label: str) -> JsonObject:
    schema = getattr(param_type, "model_json_schema", None)
    if callable(schema):
        value = schema()
    elif is_dataclass(param_type):
        value = {
            "title": param_type.__name__,
            "type": "object",
            "properties": {
                field.name: {"title": field.name, "type": "string"}
                for field in fields(param_type)
            },
        }
    else:
        raise TypeError(f"{label} must define model_json_schema() or be a dataclass")
    if not isinstance(value, dict):
        raise TypeError(f"{label} model_json_schema() must return a dict")
    return cast(JsonObject, value)
