"""The Project is the load-bearing abstraction of rlab.

A Project owns a Registry. All declarations (``@lab.experiment``, ``@lab.study``,
``@lab.workflow``, ``@lab.source``, etc.) bind to a specific project. The runner
and CLI consume a Project to know which declarations to look up.

The old shape was::

    @rlab.experiment("name", question="...")        # reads a module-level ContextVar
    def run(ctx): ...

The new shape is::

    # my_project/project.py
    import rlab
    lab = rlab.Project("my-project")

    # my_project/experiments.py
    from my_project.project import lab

    @lab.experiment("name", question="...")
    def run(ctx): ...

Why a Project (and not a Registry): users do not want a registry. They want a
project, app, suite, or workspace. The registry lives inside it
(``lab.registry``), exposed for advanced use (tests, introspection, manifests).

Identity: ``rlab.Project(name)`` returns the *same* instance for the same
name. This lets each module in a project declare its own
``lab = rlab.Project("name")`` line and still share one registry — the loader
or the first importer creates the canonical Project, and every later call
re-binds to it. Tests can pre-create a Project with a chosen registry
(``rlab.Project("name", registry=my_registry)``) and that registry will be
used by every subsequent ``rlab.Project("name")`` call for the same name.
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any

from rlab.registry.store import Registry

if TYPE_CHECKING:
    from rlab.data.model import AuditPolicy, ComponentUse, DatasetSpec, PipelineSpec

# Global project store, keyed by name. Re-creating a Project with the same
# name returns the existing instance — this is what lets every module in a
# generated project rebind to the same ``lab`` even if each module emits
# ``lab = rlab.Project("name")`` at the top of its file.
_PROJECTS: dict[str, Project] = {}
_PROJECTS_LOCK = RLock()

# Pin stack: while a pin is active, ``rlab.Project(name)`` returns the pinned
# project regardless of the requested name. This lets the experiment/study
# loaders inject a specific project into a file whose source code declares
# ``lab = rlab.Project("name")`` with its own name.
_PINNED: list[Project] = []


def _pin_lab_name(project: Project) -> Project:
    """Pin ``project`` so subsequent ``rlab.Project(...)`` calls return it."""
    _PINNED.append(project)
    return project


def _unpin_lab_name(project: Project) -> None:
    """Pop a pin pushed by ``_pin_lab_name`` (idempotent)."""
    for i in range(len(_PINNED) - 1, -1, -1):
        if _PINNED[i] is project:
            _PINNED.pop(i)
            return


class Project:
    """A research project: name + owned registry + bound decorators.

    The decorator methods (``@lab.experiment``, ``@lab.study``, ``@lab.workflow``,
    ``@lab.source``, etc.) register into ``self.registry`` directly — no global
    state, no ContextVar, no ambient mutation.

    Two projects may coexist; each has its own registry::

        lab_a = rlab.Project("team-a")
        lab_b = rlab.Project("team-b")

        @lab_a.experiment("baseline")
        def a(): ...

        @lab_b.experiment("baseline")
        def b(): ...

    The registry is exposed for advanced use (tests, introspection, manifests)::

        assert "baseline" in {r.name for r in lab_a.registry.list(EntryKind.EXPERIMENT)}
        manifest = lab_a.registry.to_manifest()

    Identity: ``rlab.Project(name)`` returns the same instance for the same
    name. This lets every module in a project declare
    ``lab = rlab.Project("name")`` at the top and share one registry. The
    first call creates the canonical project (and its registry, unless one
    was provided); later calls re-bind to it. Pass ``registry=`` on the
    first call to seed the registry with a custom one (e.g. in tests).
    """

    # Field declarations (set in __new__). We avoid @dataclass because the
    # singleton __new__ needs to control attribute assignment, and the
    # dataclass-generated __init__ would otherwise overwrite the existing
    # instance's fields on every repeated call.
    name: str
    root: Path | None
    registry: Registry
    _registry_seeded: bool

    def __new__(
        cls, name: str, root: Path | None = None, registry: Registry | None = None
    ) -> Project:
        # Loader pin: return the most recently pinned project regardless of
        # the requested name. This is the load-time override.
        if _PINNED:
            return _PINNED[-1]
        with _PROJECTS_LOCK:
            existing = _PROJECTS.get(name)
            if existing is not None:
                # Late-bind a registry only if the existing project still has
                # its default and the caller explicitly provided one.
                if (
                    registry is not None
                    and existing.registry is not registry
                    and existing._registry_seeded is False
                ):
                    existing.registry = registry
                    existing._registry_seeded = True
                # Update root only if not yet set.
                if root is not None and existing.root is None:
                    existing.root = root
                return existing
        instance = object.__new__(cls)
        instance.name = name
        instance.root = root
        instance.registry = registry if registry is not None else Registry()
        instance._registry_seeded = registry is not None
        with _PROJECTS_LOCK:
            _PROJECTS[name] = instance
        return instance

    def __repr__(self) -> str:
        return f"Project({self.name!r})"

    # --- Bound decorator methods. Each delegates to the underlying top-level
    # decorator with ``registry=self.registry`` so the registry is bound at
    # call time (when the decorator returns its ``decorate`` closure), and
    # the closure itself dispatches the registration into the bound registry
    # at decoration time. No ContextVar, no ambient state. Imports are deferred
    # to break the ``rlab.api`` ↔ ``rlab.config`` ↔ ``rlab.project`` cycle.
    #
    # Return type is ``Any`` because the per-domain decorator factories
    # (e.g. ``experiment``) use bound TypeVars (``ExperimentFn``) that we
    # cannot re-export through the generic bound-method shape. Callers see
    # the underlying callable's return type at the use site.

    def experiment(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.experiments.decorators import experiment as _experiment

        return _experiment(*args, registry=self.registry, **kwargs)

    def experiment_from_spec(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.experiments.decorators import _ExperimentDecorator

        return _ExperimentDecorator.from_spec(*args, registry=self.registry, **kwargs)

    def study(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.studies.decorators import study as _study

        return _study(*args, registry=self.registry, **kwargs)

    def workflow(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.workflows.decorators import workflow as _workflow

        return _workflow(*args, registry=self.registry, **kwargs)

    def define_workflow(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.workflows.definitions import define_workflow as _define_workflow

        return _define_workflow(*args, registry=self.registry, **kwargs)

    def evaluation(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.evaluations.decorators import evaluation as _evaluation

        return _evaluation(*args, registry=self.registry, **kwargs)

    def external_evaluation(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.evaluations.definitions import external_evaluation as _external_evaluation

        return _external_evaluation(*args, registry=self.registry, **kwargs)

    def source(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import source as _source

        return _source(*args, registry=self.registry, **kwargs)

    def transform(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import transform as _transform

        return _transform(*args, registry=self.registry, **kwargs)

    def filter(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import filter as _filter

        return _filter(*args, registry=self.registry, **kwargs)

    def group(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import group as _group

        return _group(*args, registry=self.registry, **kwargs)

    def dedup(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import dedup as _dedup

        return _dedup(*args, registry=self.registry, **kwargs)

    def sink(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import sink as _sink

        return _sink(*args, registry=self.registry, **kwargs)

    def check(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import check as _check

        return _check(*args, registry=self.registry, **kwargs)

    def metric(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import metric as _metric

        return _metric(*args, registry=self.registry, **kwargs)

    def patterns(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import patterns as _patterns

        return _patterns(*args, registry=self.registry, **kwargs)

    def component(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import component as _component

        return _component(*args, registry=self.registry, **kwargs)

    def benchmark(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.decorators import benchmark as _benchmark

        return _benchmark(*args, registry=self.registry, **kwargs)

    def substitute(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.utilities import substitute as _substitute

        return _substitute(*args, registry=self.registry, **kwargs)

    def classify(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.utilities import classify as _classify

        return _classify(*args, registry=self.registry, **kwargs)

    def predicate(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.utilities import predicate as _predicate

        return _predicate(*args, registry=self.registry, **kwargs)

    def threshold(self, *args: Any, **kwargs: Any) -> Any:
        from rlab.data.utilities import threshold as _threshold

        return _threshold(*args, registry=self.registry, **kwargs)

    # --- Factory functions (return specs, not callables).

    def pipeline(
        self,
        name: str,
        *stages: type | object | ComponentUse,
        version: str = "1.0.0",
        tags: tuple[str, ...] = (),
        description: str = "",
    ) -> PipelineSpec:
        from rlab.data.decorators import pipeline as _pipeline

        return _pipeline(
            name, *stages, version=version, tags=tags, description=description, registry=self.registry
        )

    def dataset(
        self,
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
    ) -> DatasetSpec:
        from rlab.data.decorators import dataset as _dataset

        return _dataset(
            name,
            source=source,
            pipeline=pipeline,
            sinks=sinks,
            checks=checks,
            metrics=metrics,
            audit=audit,
            version=version,
            tags=tags,
            description=description,
            registry=self.registry,
        )


__all__ = ["Project"]
