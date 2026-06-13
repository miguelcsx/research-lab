"""Evaluation model helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from rlab._typing import JsonObject, JsonValue

SCHEMA_VERSION: Final = 1

KEY_SCHEMA_VERSION: Final = "schema_version"
KEY_SUITE: Final = "suite"
KEY_NAME: Final = "name"
KEY_TASKS: Final = "tasks"
KEY_TASK: Final = "task"
KEY_METRICS: Final = "metrics"
KEY_MODEL: Final = "model"


@dataclass(frozen=True, slots=True)
class EvaluationTask:
    suite: str
    name: str
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_SUITE: self.suite,
            KEY_NAME: self.name,
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class EvaluationSuite:
    name: str
    tasks: tuple[EvaluationTask, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: self.schema_version,
            KEY_NAME: self.name,
            KEY_TASKS: _tasks(self.tasks),
        }


@dataclass(frozen=True, slots=True)
class TaskResult:
    task: str
    metrics: dict[str, float]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_TASK: self.task,
            KEY_METRICS: _metrics(self.metrics),
            KEY_SCHEMA_VERSION: self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    suite: str
    model: str
    tasks: tuple[TaskResult, ...] = field(default_factory=tuple)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            KEY_SCHEMA_VERSION: self.schema_version,
            KEY_SUITE: self.suite,
            KEY_MODEL: self.model,
            KEY_TASKS: _tasks(self.tasks),
        }


def _tasks(
    tasks: tuple[EvaluationTask, ...] | tuple[TaskResult, ...],
) -> list[JsonValue]:
    return [task.to_dict() for task in tasks]


def _metrics(metrics: dict[str, float]) -> JsonObject:
    return dict(metrics)
