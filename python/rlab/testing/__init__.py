"""Testing assertions for rlab project outputs."""

from __future__ import annotations

import json
from pathlib import Path


def assert_valid_run_dir(path: str | Path) -> None:
    run = Path(path)
    required = ["run.json", "status.txt", "params.json"]
    missing = [name for name in required if not (run / name).exists()]
    if missing:
        raise AssertionError(f"invalid run directory; missing {missing}")


def assert_metric_exists(path: str | Path, name: str) -> None:
    metrics = Path(path) / "metrics_summary.json"
    if not metrics.exists():
        raise AssertionError("metrics_summary.json does not exist")
    values = json.loads(metrics.read_text(encoding="utf-8"))
    if name not in values:
        raise AssertionError(f"metric {name!r} does not exist")


__all__ = ["assert_metric_exists", "assert_valid_run_dir"]
