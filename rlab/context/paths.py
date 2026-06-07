from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.config.models import PathConfig


class ProjectPaths(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root: Path
    runs: Path
    artifacts: Path
    manifests: tuple[Path, ...]
    reports: Path
    cache: Path

    @classmethod
    def from_config(cls, root: Path, config: PathConfig) -> "ProjectPaths":
        def resolve(path: Path) -> Path:
            return path if path.is_absolute() else root / path

        return cls(
            root=root,
            runs=resolve(config.runs),
            artifacts=resolve(config.artifacts),
            manifests=tuple(resolve(path) for path in config.manifests),
            reports=resolve(config.reports),
            cache=resolve(config.cache),
        )

    def ensure_runtime_dirs(self) -> None:
        for path in (self.runs, self.artifacts, self.reports, self.cache):
            path.mkdir(parents=True, exist_ok=True)
