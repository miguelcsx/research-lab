"""Typed local run queries for notebooks, reports, and tests."""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path

from ._typing import JsonObject, coerce_json_value


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    path: Path
    manifest: JsonObject
    params: JsonObject
    metrics: dict[str, float]


class RunQuery:
    def __init__(self, root: str | Path = ".rlab/runs") -> None:
        self.root = Path(root)

    def find(
        self,
        *,
        target: str | None = None,
        seed: int | None = None,
    ) -> tuple[RunRecord, ...]:
        records = self.all()
        return tuple(
            record
            for record in records
            if (target is None or fnmatch.fnmatch(_target(record), target))
            and (seed is None or record.manifest.get("seed") == seed)
        )

    def all(self) -> tuple[RunRecord, ...]:
        if not self.root.exists():
            return ()
        return tuple(
            record
            for path in sorted(self.root.iterdir())
            if path.is_dir() and (record := _read_run(path)) is not None
        )


def _read_run(path: Path) -> RunRecord | None:
    manifest_path = path / "run.json"
    if not manifest_path.is_file():
        return None
    manifest = _read_object(manifest_path)
    params_path = path / "params.json"
    params = _read_object(params_path) if params_path.is_file() else {}
    summary_path = path / "metrics_summary.json"
    raw_metrics = _read_object(summary_path) if summary_path.is_file() else {}
    nested = raw_metrics.get("metrics", raw_metrics)
    metrics = (
        {
            str(name): float(value)
            for name, value in nested.items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
        if isinstance(nested, dict)
        else {}
    )
    return RunRecord(path.name, path, manifest, params, metrics)


def _read_object(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return {str(key): coerce_json_value(item) for key, item in value.items()}


def _target(record: RunRecord) -> str:
    value = record.manifest.get("target", "")
    if isinstance(value, dict):
        return f"{value.get('kind', '')}:{value.get('name', '')}"
    return str(value)


__all__ = ["RunQuery", "RunRecord"]
