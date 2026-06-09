from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.registry.resolve import resolve_definition
from rlab.workflows.model import Workflow, WorkflowStep, WorkflowStepResult

WorkflowFn = TypeVar("WorkflowFn", bound=Callable[..., WorkflowStepResult])


def workflow(  # noqa: PLR0913
    name: str,
    *,
    step: str,
    description: str = "",
    cache: bool = False,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
) -> Callable[[WorkflowFn], WorkflowFn]:
    """Declare one step and compose its workflow in declaration order."""

    def decorate(run: WorkflowFn) -> WorkflowFn:
        registry = current_registry()
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
        if any(
            isinstance(item, WorkflowStep) and item.name == step_name
            for item in existing.steps
        ):
            raise ValueError(f"duplicate workflow step {step!r} in workflow {name!r}")
        merged = existing.model_copy(
            update={
                "steps": (*existing.steps, definition),
                "description": existing.description or description,
                "cache_steps": existing.cache_steps or cache,
            }
        )
        registry.replace(current.model_copy(update={"value": merged}))
        return run

    return decorate
