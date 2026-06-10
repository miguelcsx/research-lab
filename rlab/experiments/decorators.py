from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.experiments.model import Experiment
from rlab.registry.decorators import register
from rlab.registry.store import Registry
from rlab.workflows.model import WorkflowStepResult

ExperimentFn = TypeVar(
    "ExperimentFn",
    bound=Callable[[RuntimeContext], WorkflowStepResult],
)


class _ExperimentDecorator:
    """Two clean entry points: plain kwargs (common) or a pre-built spec (advanced).

    The two paths are intentionally distinct so they cannot be mixed by accident::

        @lab.experiment("name", question="...", matrix=...)         # common case
        @lab.experiment.from_spec("name", spec)                    # shared spec
    """

    def __call__(
        self,
        name: str,
        question: str,
        *,
        registry: Registry,
        **fields: object,
    ) -> Callable[[ExperimentFn], ExperimentFn]:
        spec = Experiment(question=question, **fields)

        def decorate(run: ExperimentFn) -> ExperimentFn:
            self._register(registry, name, run, spec.model_copy(update={"run": name}))
            return run

        return decorate

    @classmethod
    def from_spec(
        cls,
        name: str,
        spec: Experiment,
        *,
        registry: Registry,
    ) -> Callable[[ExperimentFn], ExperimentFn]:
        def decorate(run: ExperimentFn) -> ExperimentFn:
            cls()._register(registry, name, run, spec.model_copy(update={"run": name}))
            return run

        return decorate

    def _register(
        self,
        registry: Registry,
        name: str,
        run: ExperimentFn,
        spec: Experiment,
    ) -> None:
        register(registry, EntryKind.WORKFLOW_STEP, name, run)
        register(registry, EntryKind.EXPERIMENT, name, spec, declared_by=run)


experiment: _ExperimentDecorator = _ExperimentDecorator()
