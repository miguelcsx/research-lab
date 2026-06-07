from pathlib import Path

from pydantic import BaseModel, ConfigDict


class FileArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    path: Path
    media_type: str = "application/octet-stream"
    description: str = ""
