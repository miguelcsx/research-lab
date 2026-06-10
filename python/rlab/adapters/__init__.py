"""Adapter facade types for external research tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(slots=True)
class AdapterContext:
    """Runtime information passed to project-defined adapters."""

    project_root: Path
    run_dir: Path | None = None
    params: Mapping[str, Any] = field(default_factory=dict)

    def project_path(self, *parts: str) -> Path:
        """Return an absolute project path."""
        return self.project_root.joinpath(*parts)

    def artifact_path(self, *parts: str) -> Path:
        """Return an absolute per-run artifact path."""
        if self.run_dir is None:
            raise AdapterValidationError("adapter artifact path requested outside a run")
        return self.run_dir.joinpath("artifacts", *parts)


@dataclass(slots=True)
class AdapterResult:
    """Structured adapter result emitted back to the runtime."""

    metrics: Mapping[str, float] = field(default_factory=dict)
    artifacts: Sequence[Path] = field(default_factory=tuple)
    data: Mapping[str, Any] = field(default_factory=dict)


class AdapterValidationError(Exception):
    """Raised when an adapter cannot satisfy the runtime contract."""


class BaseAdapter:
    """Base class for Python adapters that wrap external repositories/tools.

    Subclasses should override ``command``. ``output_dirs`` may be declared as
    a class attribute to map fixed external output locations into rlab artifact
    storage without overriding a method for static mappings.
    """

    output_dirs: Mapping[str, str] = {}

    def validate(self, ctx: AdapterContext) -> None:
        """Validate adapter inputs before command execution."""
        if not ctx.project_root.exists():
            raise AdapterValidationError(f"project root does not exist: {ctx.project_root}")

    def external_output_dirs(self, ctx: AdapterContext) -> Mapping[str, str]:
        """Return external-output to artifact-store mappings."""
        self.validate(ctx)
        return dict(self.output_dirs)

    def command(self, ctx: AdapterContext):
        """Return an ExternalCommand-like object for execution."""
        self.validate(ctx)
        raise AdapterValidationError(f"{type(self).__name__}.command(ctx) must be implemented")


__all__ = ["AdapterContext", "AdapterResult", "AdapterValidationError", "BaseAdapter"]
