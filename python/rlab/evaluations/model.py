"""Evaluation model helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class EvaluationTask:
    suite: str
    name: str
    schema_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class EvaluationSuite:
    name: str
    tasks: tuple[EvaluationTask, ...] = ()
    schema_version: int = 1

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version, "name": self.name, "tasks": [task.to_dict() for task in self.tasks]}


@dataclass(slots=True)
class TaskResult:
    task: str
    metrics: dict[str, float]
    schema_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class EvaluationResult:
    suite: str
    model: str
    tasks: tuple[TaskResult, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version, "suite": self.suite, "model": self.model, "tasks": [task.to_dict() for task in self.tasks]}
