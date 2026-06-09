from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Study(BaseModel):
    """A research planning unit: question, hypotheses, design, decision rule.

    `variables` describes the design matrix the study expects (factor → choices).
    `outcomes` lists the metric names the study expects to read off resulting
    runs. `decision_rule` is plain text; humans interpret it, but it surfaces in
    reports so the rule is recorded alongside the runs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str
    hypotheses: tuple[str, ...] = ()
    domain: str = "general"
    variables: Mapping[str, tuple[JsonValue, ...]] = Field(default_factory=dict)
    outcomes: tuple[str, ...] = ()
    decision_rule: str = ""
    experiments: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()

    @property
    def planned_runs(self) -> int:
        if not self.variables:
            return 0
        total = 1
        for choices in self.variables.values():
            total *= max(1, len(tuple(choices)))
        return total
