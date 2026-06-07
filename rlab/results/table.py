from pathlib import Path

from pydantic import BaseModel, ConfigDict


class TableArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    path: Path
    format: str = "csv"
    description: str = ""
