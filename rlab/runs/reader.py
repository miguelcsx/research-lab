from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from rlab.constants import RunStatus
from rlab.manifests.run import RunManifest
from rlab.runs.layout import RunLayout


class RunReader:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.layout = RunLayout(root=self.root)

    def status(self) -> RunStatus:
        path = self.layout.status_file
        if not path.exists():
            return RunStatus.CREATED
        return RunStatus(path.read_text(encoding="utf-8").strip())

    def params(self) -> dict[str, Any]:
        path = self.layout.params_file
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def metrics(self) -> list[dict[str, Any]]:
        path = self.layout.metrics_file
        if not path.exists():
            return []
        return [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    def metrics_summary(self) -> dict[str, float]:
        path = self.layout.metrics_summary_file
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        summary: dict[str, float] = {}
        for record in self.metrics():
            name = record.get("name")
            value = record.get("value")
            if isinstance(name, str) and isinstance(value, (int, float)):
                summary[name] = float(value)
        return summary

    def notes(self) -> list[dict[str, Any]]:
        path = self.layout.notes_file
        if not path.exists():
            return []
        return [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    def manifest(self) -> RunManifest:
        path = self.layout.manifest_file
        if not path.exists():
            raise FileNotFoundError(f"No manifest at {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return RunManifest.model_validate(data)

    def results(self) -> dict[str, Any]:
        path = self.layout.results_file
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {"value": data}

    def figures(self) -> tuple[Path, ...]:
        if not self.layout.figures.exists():
            return ()
        return tuple(sorted(p for p in self.layout.figures.rglob("*") if p.is_file()))

    def tables(self) -> tuple[Path, ...]:
        if not self.layout.tables.exists():
            return ()
        return tuple(sorted(p for p in self.layout.tables.rglob("*") if p.is_file()))
