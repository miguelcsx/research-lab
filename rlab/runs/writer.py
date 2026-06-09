from __future__ import annotations

import csv
import json
import threading
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


class RunWriter:
    def __init__(self, layout: RunLayout) -> None:
        self.layout = layout
        self.layout.create()
        self._summary: dict[str, Any] | None = None

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

        # Summary is kept in memory after the first call so high-frequency
        # metric streams (training loops) do not re-read the file every event.
        if self._summary is None:
            self._summary = _load_json_dict(self.layout.metrics_summary_file)
        self._summary[name] = float(value)
        self.layout.metrics_summary_file.write_text(
            json.dumps(self._summary, indent=2) + "\n", encoding="utf-8"
        )

    def params(self, mapping: Mapping[str, Any]) -> None:
        existing = _load_json_dict(self.layout.params_file)
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


_WRITER_CACHE: dict[Path, RunWriter] = {}
_WRITER_LOCK = threading.Lock()


def writer_for(run_dir: Path) -> RunWriter:
    """Process-wide writer per run directory.

    Reusing one writer keeps the metrics summary cached in memory and avoids
    re-creating the run layout on every metric event.
    """
    with _WRITER_LOCK:
        writer = _WRITER_CACHE.get(run_dir)
        if writer is None:
            writer = RunWriter(RunLayout(root=run_dir))
            _WRITER_CACHE[run_dir] = writer
        return writer


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value
