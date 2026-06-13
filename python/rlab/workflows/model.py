"""Workflow model helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final, Protocol

from rlab._typing import JsonObject, JsonValue

SCHEMA_VERSION: Final = 1
DEFAULT_TIMEOUT_SECONDS: Final = 3600

KEY_SCHEMA_VERSION: Final = "schema_version"
KEY_NAME: Final = "name"
KEY_FN: Final = "fn"
KEY_COMMAND: Final = "command"
KEY_CWD: Final = "cwd"
KEY_TIMEOUT_SECONDS: Final = "timeout_seconds"
KEY_STEPS: Final = "steps"


class SerializableStep(Protocol):
    def to_dict(self) -> JsonObject: ...


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    name: str
    fn: Callable[..., object] | None = None
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_NAME: self.name,
            KEY_FN: _callable_name(self.fn),
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ExternalStep:
    name: str
    command: tuple[str, ...]
    cwd: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_NAME: self.name,
            KEY_COMMAND: list(self.command),
            KEY_CWD: self.cwd,
            KEY_TIMEOUT_SECONDS: self.timeout_seconds,
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class Workflow:
    name: str
    steps: tuple[WorkflowStep | ExternalStep, ...] = field(default_factory=tuple)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: self.schema_version,
            KEY_NAME: self.name,
            KEY_STEPS: _steps(self.steps),
        }


def _callable_name(fn: Callable[..., object] | None) -> str | None:
    if fn is None:
        return None

    name = getattr(fn, "__qualname__", None)
    if name is None:
        return None

    return str(name)


def _steps(steps: tuple[SerializableStep, ...]) -> list[JsonValue]:
    return [step.to_dict() for step in steps]
