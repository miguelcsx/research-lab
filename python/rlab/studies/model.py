"""Study model helpers."""

from __future__ import annotations

from dataclasses import dataclass

from rlab._typing import JsonObject


@dataclass(slots=True)
class StudyPlan:
    question: str
    experiments: tuple[str, ...] = ()
    outcomes: tuple[str, ...] = ()
    schema_version: int = 1

    def to_dict(self) -> JsonObject:
        return {
            "question": self.question,
            "experiments": list(self.experiments),
            "outcomes": list(self.outcomes),
            "schema_version": self.schema_version,
        }


@dataclass(slots=True)
class Study:
    name: str
    plan: StudyPlan
    schema_version: int = 1

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "plan": self.plan.to_dict(),
        }
