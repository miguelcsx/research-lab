"""External command descriptors for rlab."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from rlab._rlab import ExternalCommand, ExternalPath, ExternalResult, ExternalWorkspace
from rlab._typing import JsonValue

ERROR_COMMAND_NOT_IMPLEMENTED: Final = "{adapter}.command(ctx) must be implemented"

__all__ = [
    "AdapterContext",
    "AdapterValidationError",
    "BaseAdapter",
    "ExternalCommand",
    "ExternalCommandError",
    "ExternalPath",
    "ExternalResult",
    "ExternalWorkspace",
]


class ExternalCommandError(RuntimeError):
    """Raised when an external command exits unsuccessfully."""

    def __init__(self, name: str, result: ExternalResult) -> None:
        self.name = name
        self.result = result
        super().__init__(f"external command {name!r} {_failure_reason(result)}")


@dataclass(frozen=True, slots=True)
class AdapterContext:
    project_root: Path
    workspace: Path
    outputs: Path
    params: Mapping[str, JsonValue] = field(default_factory=dict)

    def project_path(self, value: str | Path) -> Path:
        return self.project_root / value

    def output_path(self, value: str | Path) -> Path:
        return self.outputs / value


class AdapterValidationError(ValueError):
    """Raised when an adapter declaration is invalid."""


class BaseAdapter:
    """Base class for project-specific external adapters."""

    workspace: ExternalWorkspace | None = None

    def prepare(self, ctx: AdapterContext) -> None:
        """Validate adapter-specific requirements before execution."""

    def command(self, ctx: AdapterContext) -> ExternalCommand:
        raise AdapterValidationError(
            ERROR_COMMAND_NOT_IMPLEMENTED.format(adapter=type(self).__name__)
        )


def _failure_reason(result: ExternalResult) -> str:
    if result.timed_out:
        return "timed out"
    return f"failed with exit code {result.exit_code}"
