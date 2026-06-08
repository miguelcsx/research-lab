from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RunLayout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root: Path

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def tables(self) -> Path:
        return self.root / "tables"

    @property
    def figures(self) -> Path:
        return self.root / "figures"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def metrics_file(self) -> Path:
        return self.root / "metrics.jsonl"

    @property
    def metrics_summary_file(self) -> Path:
        return self.root / "metrics_summary.json"

    @property
    def params_file(self) -> Path:
        return self.root / "params.json"

    @property
    def notes_file(self) -> Path:
        return self.root / "notes.jsonl"

    @property
    def status_file(self) -> Path:
        return self.root / "status.txt"

    @property
    def results_file(self) -> Path:
        return self.root / "results.json"

    @property
    def manifest_file(self) -> Path:
        return self.root / "run.yaml"

    @property
    def results(self) -> Path:
        return self.root / "results"

    def create(self) -> None:
        for directory in (self.root, self.logs, self.tables, self.figures, self.artifacts, self.results):
            directory.mkdir(parents=True, exist_ok=True)
