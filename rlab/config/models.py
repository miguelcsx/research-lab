from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProjectConfig(ConfigModel):
    name: str = "research-project"
    team: str | None = None


class PluginConfig(ConfigModel):
    autoload: bool = True
    modules: tuple[str, ...] = ("components", "benchmarks", "suites", "data")
    allow_project_overrides: bool = False


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


class LauncherConfig(ConfigModel):
    default: str = "local"
    timeout_seconds: int | None = None
    docker_image: str | None = None


class LabConfig(ConfigModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    reproducibility: ReproducibilityConfig = Field(default_factory=ReproducibilityConfig)
    launcher: LauncherConfig = Field(default_factory=LauncherConfig)
