from collections.abc import Mapping, Sequence
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rlab.constants import FailureKind
from rlab.context.resources import Resources
from rlab.experiments.matrix import Grid, Sample
from rlab.typing import JsonValue

ExperimentMatrix: TypeAlias = Mapping[str, Sequence[JsonValue]] | Grid | Sample


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: int = 1
    on: tuple[FailureKind, ...] = ()
    delay_seconds: float = 0.0


class Experiment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    # Core research fields
    question: str
    hypothesis: str = ""
    decision_criteria: str = ""
    assumptions: tuple[str, ...] = ()
    threats: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    # Execution — can be a plain dict, Grid, or Sample
    matrix: ExperimentMatrix = Field(default_factory=dict)
    run: str | None = None
    workflow: str | None = None
    benchmarks: tuple[str, ...] = ()
    evaluations: tuple[str, ...] = ()
    data: str | None = None

    # Declared outputs (contract)
    metrics: tuple[str, ...] = ()
    figures: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    required_outputs: tuple[str, ...] = ()

    # Execution control
    seeds: tuple[int, ...] = (0,)
    resources: Resources = Field(default_factory=Resources)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    after_run: tuple[str, ...] = ()

    @field_validator("matrix")
    @classmethod
    def dimensions_are_non_empty(cls, value: ExperimentMatrix) -> ExperimentMatrix:
        if isinstance(value, Mapping):
            empty = [name for name, choices in value.items() if not choices]
            if empty:
                raise ValueError(f"empty experiment dimensions: {', '.join(empty)}")
        return value
