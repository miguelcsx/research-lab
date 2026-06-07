from pathlib import Path

from rlab.manifests.run import RunManifest
from rlab.runs.index import RunIndex
from rlab.runs.layout import RunLayout
from rlab.runs.writer import RunWriter


class LocalTracking:
    def __init__(self, index: RunIndex, runs_dir: Path) -> None:
        self.index = index
        self.runs_dir = runs_dir

    def start(self, manifest: RunManifest) -> None:
        self.index.upsert(manifest, self.runs_dir / manifest.name)

    def metric(self, run_id: str, name: str, value: float, step: int | None = None) -> None:
        RunWriter(RunLayout(root=self.runs_dir / run_id)).metric(name, value, step=step)

    def finish(self, manifest: RunManifest) -> None:
        self.index.upsert(manifest, self.runs_dir / manifest.name)
