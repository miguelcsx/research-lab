from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rlab.constants import RunStatus
from rlab.runs.layout import RunLayout


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")


class RunWriter:
    def __init__(self, layout: RunLayout) -> None:
        self.layout = layout
        self.layout.create()

    def status(self, status: RunStatus) -> None:
        self.layout.status_file.write_text(status.value + "\n", encoding="utf-8")

    def metric(self, name: str, value: float, **attrs: Any) -> None:
        payload: dict[str, Any] = {
            "name": name,
            "value": float(value),
            "timestamp": _now(),
        }
        payload.update(attrs)
        _append_jsonl(self.layout.metrics_file, payload)

        summary_path = self.layout.metrics_summary_file
        summary: dict[str, float] = {}
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                summary = {}
        summary[name] = float(value)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def params(self, mapping: Mapping[str, Any]) -> None:
        existing: dict[str, Any] = {}
        if self.layout.params_file.exists():
            try:
                existing = json.loads(self.layout.params_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        existing.update(dict(mapping))
        self.layout.params_file.write_text(
            json.dumps(existing, indent=2, default=str) + "\n", encoding="utf-8"
        )

    def note(self, text: str, author: str | None = None) -> None:
        _append_jsonl(
            self.layout.notes_file,
            {"text": text, "author": author, "timestamp": _now()},
        )

    def table(
        self,
        name: str,
        rows: Iterable[Mapping[str, Any]],
        *,
        fmt: str = "csv",
    ) -> Path:
        self.layout.tables.mkdir(parents=True, exist_ok=True)
        rows_list = list(rows)
        dest = self.layout.tables / f"{name}.{fmt}"
        if fmt == "csv":
            if rows_list:
                fieldnames = list(rows_list[0].keys())
                with dest.open("w", encoding="utf-8", newline="") as fh:
                    csv_writer = csv.DictWriter(fh, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    csv_writer.writerows(rows_list)
            else:
                dest.write_text("", encoding="utf-8")
        elif fmt == "json":
            dest.write_text(json.dumps(rows_list, indent=2, default=str) + "\n", encoding="utf-8")
        else:
            raise ValueError(f"Unsupported table format: {fmt!r}")
        return dest

    def results(self, payload: Any) -> None:
        self.layout.results_file.write_text(
            json.dumps(_to_jsonable(payload), indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def error(self, message: str) -> None:
        self.layout.logs.mkdir(parents=True, exist_ok=True)
        (self.layout.logs / "error.txt").write_text(message, encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value
