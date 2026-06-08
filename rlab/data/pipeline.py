from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rlab.typing import JsonValue


class DataBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outputs: dict[str, Path]
    stats: dict[str, JsonValue] = Field(default_factory=dict)
    checks: dict[str, str] = Field(default_factory=dict)
    licenses: tuple[str, ...] = ()


class DataPipeline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sources: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    outputs: dict[str, Path] = Field(default_factory=lambda: {"data": Path("data.jsonl")})
    builder: str | None = None
    params: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_execution_mode(self) -> "DataPipeline":
        if self.builder is None and not self.sources:
            raise ValueError("DataPipeline requires sources or a builder")
        if self.builder is not None and (
            self.sources or self.transforms or self.checks or self.metrics
        ):
            raise ValueError("builder pipelines cannot declare record stages")
        return self
