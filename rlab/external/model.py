from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rlab.external.command import ExternalCommand


class ExternalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: tuple[Path, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class ExternalEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    command: ExternalCommand
    parser: str
    output: Path
    repository: str | None = None
    revision: str | None = None
