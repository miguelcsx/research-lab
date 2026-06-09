from pathlib import Path

from rlab.manifests.run import RunManifest
from rlab.runs.index import RunIndex
from rlab.runs.writer import writer_for


class LocalTracking:
    def __init__(self, index: RunIndex, runs_dir: Path) -> None:
        self.index = index
        self.runs_dir = runs_dir

    def start(self, manifest: RunManifest) -> None:
        self._upsert(manifest)

    def metric(self, run_id: str, name: str, value: float, step: int | None = None) -> None:
        writer_for(self.runs_dir / run_id).metric(name, value, step=step)

    def finish(self, manifest: RunManifest) -> None:
        self._upsert(manifest)

    def _upsert(self, manifest: RunManifest) -> None:
        self.index.upsert(
            run_id=manifest.name,
            name=manifest.name,
            operation=manifest.operation,
            status=manifest.status,
            path=self.runs_dir / manifest.name,
            created_at=manifest.created_at.isoformat(),
            parent_id=manifest.parent_run,
            tags=manifest.tags,
            params=dict(manifest.parameters),
        )
