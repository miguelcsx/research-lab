from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.suite import EvaluationSuite
from rlab.evaluations.task import EvaluationTask
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.registry.resolve import resolve_definition
from rlab.typing import Metrics

EvaluationFn = TypeVar(
    "EvaluationFn",
    bound=Callable[[Any, RuntimeContext], Metrics],
)


def evaluation(
    suite: str,
    task: str,
    *,
    baselines: tuple[str, ...] = (),
    version: str = "1.0.0",
) -> Callable[[EvaluationFn], EvaluationFn]:
    """Declare an evaluation task and compose its suite automatically."""

    def decorate(evaluator: EvaluationFn) -> EvaluationFn:
        registry = current_registry()
        definition = EvaluationTask(name=task, evaluator=evaluator)
        current = registry.try_get(EntryKind.SUITE, suite)
        if current is None:
            register(
                registry,
                EntryKind.SUITE,
                suite,
                EvaluationSuite(tasks=(definition,), baselines=baselines),
                version=version,
                declared_by=evaluator,
            )
            return evaluator

        existing = resolve_definition(current.value, EvaluationSuite)
        if any(item.name == task for item in existing.tasks):
            raise ValueError(f"duplicate evaluation task {task!r} in suite {suite!r}")
        merged = existing.model_copy(
            update={
                "tasks": (*existing.tasks, definition),
                "baselines": tuple(dict.fromkeys((*existing.baselines, *baselines))),
            }
        )
        registry.replace(current.model_copy(update={"value": merged}))
        return evaluator

    return decorate
