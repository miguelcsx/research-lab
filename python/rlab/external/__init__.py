"""External command descriptors for rlab."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ExternalCommand:
    """Command executed by an external runner."""

    args: tuple[str, ...]
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: int | None = None

    def validate(self) -> None:
        """Validate command shape before it crosses the Rust boundary."""
        if not self.args or not str(self.args[0]).strip():
            raise AdapterValidationError("external command requires at least one program argument")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise AdapterValidationError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ExternalResult:
    """Result returned by an external command."""

    exit_code: int | None
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class ExternalEvaluation:
    """External evaluation declaration."""

    name: str
    command: ExternalCommand
    parser: str | None = None
    output: Path | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise AdapterValidationError("external evaluation name cannot be empty")
        self.command.validate()


@dataclass(frozen=True, slots=True)
class AdapterContext:
    project_root: Path
    artifact_root: Path
    params: Mapping[str, Any] = field(default_factory=dict)

    def project_path(self, value: str | Path) -> Path:
        return self.project_root / value

    def artifact_path(self, value: str | Path) -> Path:
        return self.artifact_root / value


@dataclass(frozen=True, slots=True)
class AdapterResult:
    metrics: dict[str, float]
    artifacts: dict[str, str]


class AdapterValidationError(ValueError):
    """Raised when an adapter declaration is invalid."""


class BaseAdapter:
    """Base class for project-specific external adapters."""

    output_dirs: Mapping[str, str] = {}

    def prepare(self, ctx: AdapterContext) -> None:
        ctx.artifact_root.mkdir(parents=True, exist_ok=True)

    def command(self, ctx: AdapterContext) -> ExternalCommand:
        raise AdapterValidationError(f"{type(self).__name__}.command(ctx) must be implemented")

    def external_output_dirs(self, ctx: AdapterContext) -> dict[str, str]:
        self.prepare(ctx)
        return dict(self.output_dirs)


__all__ = ["AdapterContext", "AdapterResult", "AdapterValidationError", "BaseAdapter", "ExternalCommand", "ExternalEvaluation", "ExternalResult"]
