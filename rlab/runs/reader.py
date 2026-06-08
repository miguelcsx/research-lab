from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

from rlab.constants import RunStatus
from rlab.manifests.run import RunManifest
from rlab.runs.layout import RunLayout


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class RunReader:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.layout = RunLayout(root=self.root)
        self._cache: dict[str, Any] = {}

    def status(self) -> RunStatus:
        path = self.layout.status_file
        if not path.exists():
            return RunStatus.CREATED
        return RunStatus(path.read_text(encoding="utf-8").strip())

    def params(self) -> dict[str, Any]:
        if "params" not in self._cache:
            self._cache["params"] = _load_json_dict(self.layout.params_file)
        return cast(dict[str, Any], self._cache["params"])

    def metrics(self) -> list[dict[str, Any]]:
        if "metrics" not in self._cache:
            path = self.layout.metrics_file
            if not path.exists():
                self._cache["metrics"] = []
            else:
                self._cache["metrics"] = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
        return cast(list[dict[str, Any]], self._cache["metrics"])

    def metrics_summary(self) -> dict[str, float]:
        if "metrics_summary" not in self._cache:
            path = self.layout.metrics_summary_file
            if path.exists():
                data = _load_json_dict(path)
                if data:
                    self._cache["metrics_summary"] = data
                    return cast(dict[str, float], self._cache["metrics_summary"])
            summary: dict[str, float] = {}
            for record in self.metrics():
                name = record.get("name")
                value = record.get("value")
                if isinstance(name, str) and isinstance(value, (int, float)):
                    summary[name] = float(value)
            self._cache["metrics_summary"] = summary
        return cast(dict[str, float], self._cache["metrics_summary"])

    def notes(self) -> list[dict[str, Any]]:
        if "notes" not in self._cache:
            path = self.layout.notes_file
            if not path.exists():
                self._cache["notes"] = []
            else:
                self._cache["notes"] = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
        return cast(list[dict[str, Any]], self._cache["notes"])

    def manifest(self) -> RunManifest:
        if "manifest" not in self._cache:
            path = self.layout.manifest_file
            if not path.exists():
                raise FileNotFoundError(f"No manifest at {path}")
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            self._cache["manifest"] = RunManifest.model_validate(data)
        return cast(RunManifest, self._cache["manifest"])

    def results(self) -> dict[str, Any]:
        if "results" not in self._cache:
            data = _load_json_dict(self.layout.results_file)
            self._cache["results"] = data if data else {}
        return cast(dict[str, Any], self._cache["results"])

    def figures(self) -> tuple[Path, ...]:
        if "figures" not in self._cache:
            if not self.layout.figures.exists():
                self._cache["figures"] = ()
            else:
                self._cache["figures"] = tuple(
                    sorted(p for p in self.layout.figures.rglob("*") if p.is_file())
                )
        return cast(tuple[Path, ...], self._cache["figures"])

    def tables(self) -> tuple[Path, ...]:
        if "tables" not in self._cache:
            if not self.layout.tables.exists():
                self._cache["tables"] = ()
            else:
                self._cache["tables"] = tuple(
                    sorted(p for p in self.layout.tables.rglob("*") if p.is_file())
                )
        return cast(tuple[Path, ...], self._cache["tables"])
