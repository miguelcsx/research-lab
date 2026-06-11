"""Project facade, singleton routing, and bound declaration decorators."""

from __future__ import annotations

import inspect
import json
import os
import threading
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterator

from ._decorators import decorator_factory

_LOCK = threading.RLock()
_PROJECTS: dict[str, "Project"] = {}
_PIN_STACK: list["Project"] = []


def _default_project_name() -> str:
    try:
        from ._rlab import load_config

        return str(load_config(None).project_name)
    except Exception:
        return Path.cwd().name


class Project:
    """Python facade for rlab project declarations.

    ``Project()`` is zero-config friendly. During runner imports the active
    project is pinned, so declarations register into the Rust CLI request's
    project even if user modules construct their own ``Project()`` instance.
    """

    def __new__(
        cls, name: str | None = None, root: str | Path | None = None
    ) -> "Project":
        with _LOCK:
            if _PIN_STACK:
                return _PIN_STACK[-1]
            resolved = name or _default_project_name()
            existing = _PROJECTS.get(resolved)
            if existing is not None:
                return existing
            instance = super().__new__(cls)
            _PROJECTS[resolved] = instance
            return instance

    def __init__(self, name: str | None = None, root: str | Path | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        self.name = name or _default_project_name()
        self.root = Path(root) if root is not None else Path.cwd()
        self._records: list[dict[str, Any]] = []
        self._callables: dict[tuple[str, str], Any] = {}
        self._initialized = True

    @property
    def records(self) -> list[dict[str, Any]]:
        """Return declarative registry records collected in this process."""
        return list(self._records)

    def resolve(self, kind: str, name: str) -> Any:
        """Resolve a process-local callable by kind/name."""
        key = (kind, name)
        try:
            return self._callables[key]
        except KeyError as exc:
            raise KeyError(f"no callable registered for {kind}:{name}") from exc

    def record(self, kind: str, name: str) -> dict[str, Any]:
        """Return the declarative registry record for a kind/name pair."""
        for record in self._records:
            if record.get("kind") == kind and record.get("name") == name:
                return dict(record)
        raise KeyError(f"no registry record for {kind}:{name}")

    def experiment(self, name: str, **metadata: Any):
        """Register a Python experiment callable."""
        return decorator_factory(self, "experiment", name, metadata)

    def study(self, name: str, **metadata: Any):
        """Register a study declaration."""
        return decorator_factory(self, "study", name, metadata)

    def study_from_spec(self, name: str, spec: Any):
        """Register a study from a reusable spec object."""
        return decorator_factory(self, "study", name, {"spec": _jsonable_spec(spec)})

    def experiment_from_spec(self, name: str, spec: Any):
        """Register an experiment from a reusable spec object."""
        return decorator_factory(
            self, "experiment", name, {"spec": _jsonable_spec(spec)}
        )

    def external_evaluation(self, name: str, **metadata: Any):
        """Register an external-command evaluation declaration."""

        def decorate(obj: Any = None) -> Any:
            target = obj if obj is not None else _SentinelCallable(name)
            self._register(
                kind="external_evaluation", name=name, obj=target, metadata=metadata
            )
            return target

        return decorate

    def adapter(self, name: str, **metadata: Any):
        """Register an adapter class."""
        return decorator_factory(self, "adapter", name, metadata)

    def source(self, name: str, **metadata: Any):
        """Register a dataset source class or callable."""
        return decorator_factory(self, "source", name, metadata)

    def transform(self, name: str, **metadata: Any):
        """Register a record-level transform class or callable."""
        return decorator_factory(self, "transform", name, metadata)

    def filter(self, name: str, **metadata: Any):
        """Register a record-level filter class or callable."""
        return decorator_factory(self, "filter", name, metadata)

    def group(self, name: str, **metadata: Any):
        """Register a batch-level grouping stage."""
        return decorator_factory(self, "group", name, metadata)

    def dedup(self, name: str, **metadata: Any):
        """Register a batch-level deduplication stage."""
        return decorator_factory(self, "dedup", name, metadata)

    def sink(self, name: str, **metadata: Any):
        """Register a dataset sink."""
        return decorator_factory(self, "sink", name, metadata)

    def check(self, name: str, **metadata: Any):
        """Register a dataset check."""
        return decorator_factory(self, "check", name, metadata)

    def metric(self, name: str, **metadata: Any):
        """Register a dataset metric."""
        return decorator_factory(self, "metric", name, metadata)

    def loader(self, name: str, **metadata: Any):
        """Register a loader — a component that resolves external paths.

        A loader is a class that exposes ``load(path)`` and is invoked
        when a target reference has the form ``<kind>:<loader>:<path>``.
        Loaders are how projects integrate external resources (model
        registries, artifact stores, dataset hubs) without rlab needing
        vendor-specific code.
        """
        return decorator_factory(self, "loader", name, metadata)

    def pipeline(
        self,
        name: str,
        *stages: Any,
        version: str = "1",
        tags: list[str] | tuple[str, ...] = (),
        description: str | None = None,
    ):
        """Register a pipeline declaration."""
        metadata = {
            "stages": [_jsonable_spec(stage) for stage in stages],
            "version": version,
            "tags": list(tags),
            "description": description,
        }
        sentinel = _SentinelCallable(name)
        self._register(kind="pipeline", name=name, obj=sentinel, metadata=metadata)
        return name

    def dataset(self, name: str, **metadata: Any):
        """Register a dataset declaration."""
        sentinel = _SentinelCallable(name)
        self._register(kind="dataset", name=name, obj=sentinel, metadata=metadata)
        # Store pre-configured runtime callables so the runner can use them
        # without deserializing the JSON-spec metadata back to typed objects.
        source = metadata.get("source")
        if source is not None and not isinstance(source, str):
            self._callables[("dataset_source", name)] = source
        sink = metadata.get("sink")
        sinks = metadata.get("sinks") or (
            [sink] if sink is not None and not isinstance(sink, str) else []
        )
        for index, s in enumerate(sinks):
            if s is not None and not isinstance(s, str):
                self._callables[("dataset_sink", f"{name}:{index}")] = s
        return name

    def define_workflow(self, name: str, *, steps: Any):
        """Register a workflow assembled imperatively from step descriptors."""
        metadata = {"steps": [_jsonable_spec(step) for step in steps]}
        sentinel = _SentinelCallable(name)
        self._register(kind="workflow", name=name, obj=sentinel, metadata=metadata)
        return sentinel

    def component(self, kind: str, name: str, **metadata: Any):
        """Register a reusable component class/object."""
        values = dict(metadata)
        values["component_kind"] = kind
        return decorator_factory(self, "component", name, values)

    def benchmark(self, name: str, *, target: str, **metadata: Any):
        """Register a benchmark callable."""
        values = dict(metadata)
        values["target"] = target
        return decorator_factory(self, "benchmark", name, values)

    def workflow(self, name: str, *, step: str, **metadata: Any):
        """Register a workflow step callable."""
        values = dict(metadata)
        values["step"] = step
        return decorator_factory(self, "workflow", name, values)

    def evaluation(self, suite: str, task: str, **metadata: Any):
        """Register an evaluation task callable."""
        values = dict(metadata)
        values["suite"] = suite
        values["task"] = task
        return decorator_factory(self, "evaluation", f"{suite}.{task}", values)

    def result_schema(self, name: str, **metadata: Any):
        """Register a result schema class."""
        return decorator_factory(self, "result_schema", name, metadata)

    def _register(
        self, *, kind: str, name: str, obj: Any, metadata: dict[str, Any]
    ) -> None:
        _validate_identifier(kind, name)
        module = str(getattr(obj, "__module__", ""))
        qualname = str(getattr(obj, "__qualname__", getattr(obj, "__name__", "")))
        try:
            source = inspect.getsourcefile(obj) or ""
        except (TypeError, OSError):
            source = ""
        description = _first_doc_line(obj)
        if not isinstance(
            obj, (_SentinelCallable, _WorkflowCallable)
        ) and self._is_strict_unstable(kind=kind, qualname=qualname, source=source):
            raise ValueError(f"unstable strict declaration for {kind}:{name}")
        metadata_copy = {key: _jsonable_spec(value) for key, value in metadata.items()}
        version = str(metadata_copy.pop("version", "1"))
        tags = list(metadata_copy.pop("tags", []))
        _assert_jsonable(metadata_copy, f"metadata for {kind}:{name}")
        record = {
            "schema_version": 1,
            "kind": kind,
            "name": name,
            "version": version,
            "module": module,
            "qualname": qualname,
            "source": _relative_source(source, self.root),
            "tags": tags,
            "description": description,
            "metadata": metadata_copy,
        }
        key = (kind, name)
        if key in self._callables:
            if kind == "workflow" and isinstance(metadata_copy.get("step"), str):
                step_name = str(metadata_copy["step"])
                self._append_workflow_step(name, step_name, obj, metadata_copy, record)
                return
            raise ValueError(f"duplicate registry declaration: {kind}:{name}")
        if kind == "workflow" and isinstance(metadata_copy.get("step"), str):
            step_name = str(metadata_copy["step"])
            record["metadata"] = {
                "steps": [_workflow_step_metadata(step_name, record, metadata_copy)]
            }
            self._callables[("workflow_step", f"{name}:{step_name}")] = obj
            self._callables[key] = _WorkflowCallable(name)
        else:
            self._callables[key] = obj
        self._records.append(record)
        component_kind = metadata_copy.get("component_kind")
        if (
            kind == "component"
            and isinstance(component_kind, str)
            and component_kind.strip()
        ):
            self._callables[(component_kind, name)] = obj

    def _append_workflow_step(
        self,
        workflow_name: str,
        step_name: str,
        obj: Any,
        metadata: dict[str, Any],
        record: dict[str, Any],
    ) -> None:
        for existing in self._records:
            if (
                existing.get("kind") == "workflow"
                and existing.get("name") == workflow_name
            ):
                existing_metadata = existing.setdefault("metadata", {})
                steps = existing_metadata.setdefault("steps", [])
                if not isinstance(steps, list):
                    raise ValueError(
                        f"workflow {workflow_name} has invalid steps metadata"
                    )
                if any(
                    step.get("name") == step_name
                    for step in steps
                    if isinstance(step, dict)
                ):
                    raise ValueError(
                        f"duplicate workflow step: {workflow_name}:{step_name}"
                    )
                steps.append(_workflow_step_metadata(step_name, record, metadata))
                self._callables[("workflow_step", f"{workflow_name}:{step_name}")] = obj
                return
        raise ValueError(
            f"workflow record not found while adding step: {workflow_name}"
        )

    def _is_strict_unstable(self, *, kind: str, qualname: str, source: str) -> bool:
        strict = os.environ.get("RLAB_RUNNER_STRICT") == "1"
        if not strict:
            return False
        if not source or source.startswith("<"):
            return True
        if "<lambda>" in qualname:
            return True
        if "<locals>" in qualname:
            return True
        return False


def _validate_identifier(kind: str, name: str) -> None:
    if not kind.strip() or not name.strip():
        raise ValueError("registry kind and name are required")
    invalid = [char for char in name if not (char.isalnum() or char in "._-:")]
    if invalid:
        raise ValueError(f"invalid registry name {name!r}")


def _assert_jsonable(value: Any, label: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise TypeError(f"{label} must be JSON serializable") from exc


def _first_doc_line(obj: Any) -> str:
    doc = inspect.getdoc(obj) or ""
    if not doc:
        return ""
    return doc.strip().splitlines()[0]


def _relative_source(source: str, root: Path) -> str:
    if not source:
        return ""
    path = Path(source)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


@contextmanager
def pinned_project(project: Project) -> Iterator[None]:
    """Pin a project during dynamic import."""
    with _LOCK:
        _PIN_STACK.append(project)
    try:
        yield
    finally:
        with _LOCK:
            if _PIN_STACK and _PIN_STACK[-1] is project:
                _PIN_STACK.pop()
            elif project in _PIN_STACK:
                _PIN_STACK.remove(project)


def _workflow_step_metadata(
    step_name: str, record: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    values = dict(metadata)
    values.pop("step", None)
    return {
        "name": step_name,
        "module": record["module"],
        "qualname": record["qualname"],
        "source": record["source"],
        "metadata": values,
    }


class _WorkflowCallable:
    def __init__(self, name: str) -> None:
        self.__name__ = name
        self.__qualname__ = name
        self.__module__ = "rlab.generated"

    def __call__(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "workflow sentinels are declarative and are executed by registered workflow steps"
        )


class _SentinelCallable:
    def __init__(self, name: str) -> None:
        self.__name__ = name
        self.__qualname__ = name
        self.__module__ = "rlab.generated"

    def __call__(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("declarative sentinel cannot be executed directly")


def _jsonable_spec(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if hasattr(value, "to_dict"):
        return _jsonable_spec(value.to_dict())
    if hasattr(value, "model_dump"):
        return _jsonable_spec(value.model_dump())
    rlab_ref = getattr(type(value), "__rlab_ref__", None)
    if rlab_ref and is_dataclass(value) and not isinstance(value, type):
        config = {k: _jsonable_spec(v) for k, v in asdict(value).items()}
        return {"ref": rlab_ref, **config} if config else {"ref": rlab_ref}
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable_spec(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable_spec(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_spec(child) for child in value]
    if hasattr(value, "__dict__") and not callable(value):
        return {str(key): _jsonable_spec(child) for key, child in vars(value).items()}
    return value
