from pydantic import BaseModel, ConfigDict, Field


class TaskResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    metrics: dict[str, float]


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    suite: str
    model: str
    tasks: tuple[TaskResult, ...]


class LeaderboardResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    suite: str
    models: dict[str, dict[str, float]] = Field(default_factory=dict)
