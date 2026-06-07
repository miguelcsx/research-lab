from pydantic import BaseModel, ConfigDict, Field

from rlab.constants import FailureKind
from rlab.typing import JsonValue


class ExperimentStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    params: dict[str, JsonValue]
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
    failure_kind: FailureKind = FailureKind.UNKNOWN


class ExperimentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    steps: tuple[ExperimentStep, ...]

    @property
    def successful_steps(self) -> tuple[ExperimentStep, ...]:
        return tuple(s for s in self.steps if s.error is None)

    @property
    def failed_steps(self) -> tuple[ExperimentStep, ...]:
        return tuple(s for s in self.steps if s.error is not None)

    @property
    def is_partial(self) -> bool:
        return bool(self.failed_steps) and bool(self.successful_steps)
