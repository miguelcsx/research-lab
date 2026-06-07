from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
