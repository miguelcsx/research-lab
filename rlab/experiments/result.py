from pydantic import BaseModel, ConfigDict, Field

from rlab.typing import JsonValue


class ExperimentStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    params: dict[str, JsonValue]
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ExperimentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    steps: tuple[ExperimentStep, ...]
