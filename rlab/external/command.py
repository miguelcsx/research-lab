from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ExternalCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    args: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int | None = None
