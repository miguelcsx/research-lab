from pathlib import Path

from pydantic import BaseModel, ConfigDict


class LogArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    path: Path
    description: str = ""
