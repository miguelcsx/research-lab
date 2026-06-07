from pathlib import Path

from pydantic import BaseModel, ConfigDict


class FigureArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    path: Path
    formats: tuple[str, ...] = ("png",)
    description: str = ""
