"""Workflow model helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class WorkflowStep:
    name: str
    fn: Callable[..., Any] | None = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["fn"] = (
            getattr(self.fn, "__qualname__", None) if self.fn is not None else None
        )
        return value


@dataclass(slots=True)
class ExternalStep:
    name: str
    command: tuple[str, ...]
    cwd: str | None = None
    timeout_seconds: int = 3600
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Workflow:
    name: str
    steps: tuple[WorkflowStep | ExternalStep, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
        }
