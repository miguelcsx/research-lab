"""External command descriptors for rlab."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ExternalPath:
    """One path expected by an external tool inside its workspace."""

    path: str
    name: str

    def validate(self) -> None:
        _validate_relative(self.path, "external path")
        _validate_relative(self.name, "managed path name")


@dataclass(frozen=True, slots=True)
class ExternalWorkspace:
    """Declarative filesystem contract for an external tool."""

    source_param: str
    default_source: str
    ignored: tuple[str, ...] = ()
    cached: tuple[ExternalPath, ...] = ()
    outputs: tuple[ExternalPath, ...] = ()

    def validate(self) -> None:
        if not self.source_param.strip():
            raise AdapterValidationError("workspace source_param cannot be empty")
        if not self.default_source.strip():
            raise AdapterValidationError("workspace default_source cannot be empty")
        paths = (*self.cached, *self.outputs)
        for path in paths:
            path.validate()
        if len({path.path for path in paths}) != len(paths):
            raise AdapterValidationError("workspace paths must be unique")
        if len({path.name for path in self.cached}) != len(self.cached):
            raise AdapterValidationError("cached path names must be unique")
        if len({path.name for path in self.outputs}) != len(self.outputs):
            raise AdapterValidationError("output path names must be unique")


@dataclass(frozen=True, slots=True)
class ExternalCommand:
    """Command executed by an external runner."""

    args: tuple[str, ...]
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: int | None = None
    output_root: Path | None = None
    artifacts: tuple[str, ...] = ()

    def validate(self) -> None:
        """Validate command shape before it crosses the Rust boundary."""
        if not self.args or not str(self.args[0]).strip():
            raise AdapterValidationError(
                "external command requires at least one program argument"
            )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise AdapterValidationError("timeout_seconds must be positive")
        if self.artifacts and self.output_root is None:
            raise AdapterValidationError(
                "artifact patterns require an external command output_root"
            )
        for pattern in self.artifacts:
            _validate_relative(pattern, "artifact pattern")


@dataclass(frozen=True, slots=True)
class ExternalResult:
    """Result returned by an external command."""

    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


class ExternalCommandError(RuntimeError):
    """Raised when an external command exits unsuccessfully."""

    def __init__(self, name: str, result: ExternalResult) -> None:
        self.name = name
        self.result = result
        reason = (
            "timed out"
            if result.timed_out
            else f"failed with exit code {result.exit_code}"
        )
        super().__init__(f"external command {name!r} {reason}")


@dataclass(frozen=True, slots=True)
class AdapterContext:
    project_root: Path
    workspace: Path
    outputs: Path
    params: Mapping[str, Any] = field(default_factory=dict)

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
            f"{type(self).__name__}.command(ctx) must be implemented"
        )


def _validate_relative(value: str, label: str) -> None:
    path = Path(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        raise AdapterValidationError(f"{label} must be a non-empty relative path")


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
