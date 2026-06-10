from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.registry.decorators import register
from rlab.registry.resolve import resolve_definition
from rlab.registry.store import Registry
from rlab.workflows.model import Workflow, WorkflowStep, WorkflowStepResult

WorkflowFn = TypeVar("WorkflowFn", bound=Callable[..., WorkflowStepResult])


def workflow(
    name: str,
    *,
    step: str,
    description: str = "",
    cache: bool = False,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Callable[[WorkflowFn], WorkflowFn]:
    """Declare one step and compose its workflow in declaration order.

    ``registry`` is required — pass the ``Project.registry`` to register into.
    """

    def decorate(run: WorkflowFn) -> WorkflowFn:
        step_name = f"{name}.{step}"
        register(
            registry,
            EntryKind.WORKFLOW_STEP,
            step_name,
            run,
            version=version,
            tags=tags,
        )
        definition = WorkflowStep(name=step_name, description=description, fn=run)
        current = registry.try_get(EntryKind.WORKFLOW, name)
        if current is None:
            register(
                registry,
                EntryKind.WORKFLOW,
                name,
                Workflow(
                    steps=(definition,),
                    description=description,
                    cache_steps=cache,
                ),
                version=version,
                tags=tags,
                declared_by=run,
            )
            return run

        existing = resolve_definition(current.value, Workflow)
        merged = existing.add(definition, description=description, cache_steps=cache)
        registry.replace(current.model_copy(update={"value": merged}))
        return run

    return decorate
