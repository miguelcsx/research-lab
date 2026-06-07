from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DataPipeline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sources: tuple[str, ...]
    transforms: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    outputs: dict[str, Path] = Field(default_factory=lambda: {"data": Path("data.jsonl")})
