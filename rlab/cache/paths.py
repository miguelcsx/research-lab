from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CachePaths(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root: Path

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    @property
    def external(self) -> Path:
        return self.root / "external"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def indexes(self) -> Path:
        return self.root / "indexes"
