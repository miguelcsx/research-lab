from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rlab.config.models import LabConfig
from rlab.context.paths import ProjectPaths
from rlab.context.resources import Resources
from rlab.registry.store import Registry
from rlab.typing import JsonValue


class RuntimeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: LabConfig
    paths: ProjectPaths
    registry: Registry
    run_id: str | None = None
    run_dir: Path | None = None
    seed: int = 0
    params: dict[str, JsonValue] = Field(default_factory=dict)
    resources: Resources = Field(default_factory=Resources)

    def artifact_path(self, relative: str) -> Path:
        if self.run_dir is None:
            raise RuntimeError("Runtime context has no active run")
        path = self.run_dir / "artifacts" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
