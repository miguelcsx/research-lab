from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExternalCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    args: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int | None = None

    @field_validator("args", mode="before")
    @classmethod
    def _coerce_args(cls, value: object) -> object:
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Sequence) and not isinstance(value, tuple):
            return tuple(str(part) for part in value)
        return value
