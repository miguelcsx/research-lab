from __future__ import annotations

from rlab.constants import EntryKind
from rlab.registry.decorators import register
from rlab.registry.store import Registry
from rlab.workflows.model import ExternalStep, Workflow, WorkflowStep


def define_workflow(  # noqa: PLR0913
    name: str,
    *,
    steps: tuple[str | WorkflowStep | ExternalStep, ...],
    description: str = "",
    cache: bool = False,
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
    registry: Registry,
) -> Workflow:
    """Register an immutable workflow assembled from explicit step objects.

    ``registry`` is required — pass the ``Project.registry`` to register into.
    """
    definition = Workflow(
        steps=steps,
        description=description,
        cache_steps=cache,
    )
    return register(
        registry,
        EntryKind.WORKFLOW,
        name,
        definition,
        version=version,
        tags=tags,
    )
