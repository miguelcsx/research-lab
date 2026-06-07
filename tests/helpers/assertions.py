from __future__ import annotations

from pathlib import Path

from rlab.runs.reader import RunReader


def assert_file_contains(path: Path, expected: str) -> None:
    assert path.exists(), f"Missing file: {path}"
    assert expected in path.read_text(encoding="utf-8")


def assert_run_has_metric(run_dir: Path, metric_name: str) -> None:
    metrics = RunReader(run_dir).metrics()
    assert any(row["name"] == metric_name for row in metrics), metrics


def assert_paths_exist(*paths: Path) -> None:
    missing = [path for path in paths if not path.exists()]
    assert not missing, f"Missing paths: {missing}"
