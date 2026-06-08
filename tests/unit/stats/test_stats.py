from __future__ import annotations

from pathlib import Path

from rlab.runs.layout import RunLayout
from rlab.runs.writer import RunWriter
from rlab.stats.bootstrap import bootstrap_confidence_interval
from rlab.stats.compare import MetricComparison, compare_metric_arrays, compare_runs


def test_bootstrap_basic() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    point, lower, upper = bootstrap_confidence_interval(
        values, confidence=0.95, repetitions=500, seed=42
    )
    assert lower <= point <= upper
    assert lower < upper


def test_bootstrap_empty_returns_zeros() -> None:
    point, lower, upper = bootstrap_confidence_interval([])
    assert point == 0.0
    assert lower == 0.0
    assert upper == 0.0


def test_compare_metric_arrays() -> None:
    baseline = [1.0, 2.0, 3.0]
    candidate = [2.0, 3.0, 4.0]
    result = compare_metric_arrays(baseline, candidate, metric="score")
    assert isinstance(result, MetricComparison)
    assert result.baseline == 2.0
    assert result.candidate == 3.0
    assert result.delta == 1.0


def test_compare_runs_reads_metrics(tmp_path: Path) -> None:
    base_layout = RunLayout(root=tmp_path / "base")
    base_layout.create()
    RunWriter(base_layout).metric("score", 1.0)

    cand_layout = RunLayout(root=tmp_path / "cand")
    cand_layout.create()
    RunWriter(cand_layout).metric("score", 2.0)

    result = compare_runs(base_layout.root, cand_layout.root, "score")
    assert result.metric == "score"
    assert result.baseline == 1.0
    assert result.candidate == 2.0
