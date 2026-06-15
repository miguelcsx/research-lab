from __future__ import annotations

from pathlib import Path

import pytest

from rlab.testing import assert_metric_exists, assert_valid_run_dir


def test_testing_helpers_are_rust_backed(tmp_path: Path) -> None:
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / "status.txt").write_text("completed", encoding="utf-8")
    (tmp_path / "params.json").write_text("{}", encoding="utf-8")
    (tmp_path / "metrics_summary.json").write_text(
        '{"accuracy": 0.9}', encoding="utf-8"
    )

    assert_valid_run_dir(tmp_path)
    assert_metric_exists(tmp_path, "accuracy")

    with pytest.raises(AssertionError):
        assert_metric_exists(tmp_path, "loss")


def test_testing_helpers_report_invalid_run_dir(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="invalid run directory"):
        assert_valid_run_dir(tmp_path)
