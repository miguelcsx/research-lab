from __future__ import annotations

from pathlib import Path

import pytest

from rlab.errors_analysis.compare import ErrorComparison, compare_runs_errors


def test_compare_runs_errors_no_records(tmp_path: Path) -> None:
    base = tmp_path / "baseline"
    cand = tmp_path / "candidate"
    base.mkdir()
    cand.mkdir()
    (base / "results.json").write_text('{"records": []}')
    (cand / "results.json").write_text('{"records": []}')

    result = compare_runs_errors(base, cand, metric="accuracy", by="category")
    assert isinstance(result, ErrorComparison)
    assert result.regressions == ()
    assert result.improvements == ()
    assert result.metric == "accuracy"


def test_compare_runs_errors_detects_regression(tmp_path: Path) -> None:
    base = tmp_path / "baseline"
    cand = tmp_path / "candidate"
    base.mkdir()
    cand.mkdir()
    (base / "results.json").write_text('{"records": [{"category": "A", "accuracy": 0.8}]}')
    (cand / "results.json").write_text('{"records": [{"category": "A", "accuracy": 0.7}]}')

    result = compare_runs_errors(base, cand, metric="accuracy", by="category")
    assert len(result.regressions) == 1
    assert result.regressions[0].category == "A"
    assert result.regressions[0].delta == pytest.approx(-0.1)
