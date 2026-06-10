from __future__ import annotations

from pathlib import Path

from rlab.constants import EntryKind
from rlab.external.command import ExternalCommand
from rlab.external.model import ExternalEvaluation
from rlab.registry.decorators import register
from rlab.registry.store import Registry


def external_evaluation(  # noqa: PLR0913
    name: str,
    *,
    command: ExternalCommand | tuple[str, ...],
    output: Path = Path("metrics.json"),
    parser: str = "json",
    repository: str | None = None,
    revision: str | None = None,
    version: str = "1.0.0",
    registry: Registry,
) -> ExternalEvaluation:
    """Register an immutable external evaluation without a provider function.

    ``registry`` is required — pass the ``Project.registry`` to register into.
    """
    resolved_command = (
        command if isinstance(command, ExternalCommand) else ExternalCommand(args=command)
    )
    definition = ExternalEvaluation(
        name=name,
        version=version,
        command=resolved_command,
        output=output,
        parser=parser,
        repository=repository,
        revision=revision,
    )
    return register(
        registry,
        EntryKind.EXTERNAL_SUITE,
        name,
        definition,
        version=version,
    )
