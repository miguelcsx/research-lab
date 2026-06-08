from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from rlab.constants import RunStatus
from rlab.runs.layout import RunLayout


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def current_status(root: Path) -> RunStatus:
    path = RunLayout(root=root).status_file
    if not path.exists():
        return RunStatus.CREATED
    return RunStatus(path.read_text(encoding="utf-8").strip())


def _set_status(root: Path, status: RunStatus) -> None:
    layout = RunLayout(root=root)
    layout.create()
    layout.status_file.write_text(status.value + "\n", encoding="utf-8")
    _patch_manifest(layout, {"status": status.value, "updated_at": _now()})


def _load_yaml_dict(path: Path) -> dict[str, Any] | None:
    """Return parsed YAML dict, or None if the file is missing or unparseable."""
    if not path.exists():
        return None
    try:
        result = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return result if isinstance(result, dict) else {}


def _patch_manifest(layout: RunLayout, fields: dict[str, object]) -> None:
    data = _load_yaml_dict(layout.manifest_file)
    if data is None:
        return
    data.update(fields)
    layout.manifest_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def start_run(root: Path) -> None:
    _set_status(root, RunStatus.RUNNING)


def finish_run(root: Path) -> None:
    _set_status(root, RunStatus.COMPLETED)


def cancel_run(root: Path) -> None:
    _set_status(root, RunStatus.CANCELLED)


def fail_run(root: Path, error: str) -> None:
    layout = RunLayout(root=root)
    layout.create()
    layout.logs.mkdir(parents=True, exist_ok=True)
    (layout.logs / "error.txt").write_text(error, encoding="utf-8")
    _set_status(root, RunStatus.FAILED)
    _patch_manifest(layout, {"error": error})


def mark_stale(root: Path) -> None:
    _set_status(root, RunStatus.STALE)


def resume_run(root: Path) -> None:
    _set_status(root, RunStatus.RUNNING)
