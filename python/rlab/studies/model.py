"""Study model helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class StudyPlan:
    question: str
    experiments: tuple[str, ...] = ()
    outcomes: tuple[str, ...] = ()
    schema_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Study:
    name: str
    plan: StudyPlan
    schema_version: int = 1

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "plan": self.plan.to_dict(),
        }
