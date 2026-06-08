from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from rlab.project.modules import ModulesConfig

T = TypeVar("T", bound=BaseModel)


class ConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProjectConfig(ConfigModel):
    name: str = "research-project"
    team: str | None = None
    owner: str | None = None


class PathConfig(ConfigModel):
    runs: Path = Path("runs")
    artifacts: Path = Path("artifacts")
    manifests: tuple[Path, ...] = (Path("manifests"),)
    reports: Path = Path("reports")
    cache: Path = Path(".rlab")


class TrackingConfig(ConfigModel):
    backend: str = "local"


class ArtifactConfig(ConfigModel):
    backend: str = "local"


class ReproducibilityConfig(ConfigModel):
    capture_git: bool = True
    capture_diff: bool = True
    capture_env: bool = True
    capture_packages: bool = True
    capture_lockfile: bool = True
    capture_command: bool = True
    capture_data_manifests: bool = True
    allow_dirty: bool = False
    env_allowlist: tuple[str, ...] = ()


class LauncherConfig(ConfigModel):
    default: str = "local"
    jobs: int = 1
    timeout_seconds: int | None = None
    docker_image: str | None = None


class LabConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    modules: ModulesConfig = Field(default_factory=ModulesConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    reproducibility: ReproducibilityConfig = Field(default_factory=ReproducibilityConfig)
    launcher: LauncherConfig = Field(default_factory=LauncherConfig)

    def section(self, name: str, schema: type[T] | None = None) -> Any:
        raw = self.model_extra.get(name) if self.model_extra else None
        if raw is None:
            return None
        if schema is not None:
            return schema.model_validate(raw)
        return raw
