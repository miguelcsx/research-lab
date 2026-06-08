from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rlab.external.command import ExternalCommand


class ExternalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: tuple[Path, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class ExternalEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str = "1.0.0"
    command: ExternalCommand
    parser: str = "json"
    output: Path = Path("metrics.json")
    repository: str | None = None
    revision: str | None = None

    @field_validator("command", mode="before")
    @classmethod
    def _coerce_command(cls, value: object) -> object:
        if isinstance(value, ExternalCommand):
            return value
        if isinstance(value, str):
            return ExternalCommand(args=(value,))
        if isinstance(value, Sequence):
            return ExternalCommand(args=tuple(str(part) for part in value))
        return value

    @model_validator(mode="after")
    def _default_output(self) -> "ExternalEvaluation":
        if str(self.output) == "metrics.json" and self.command.cwd is not None:
            object.__setattr__(self, "output", self.command.cwd / "metrics.json")
        return self
