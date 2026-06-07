from __future__ import annotations

from pathlib import Path

import pytest

from rlab.constants import Direction
from rlab.results.bundle import ResultBundle, bundle_from_metrics, empty_bundle
from rlab.results.figure import FigureArtifact
from rlab.results.file import FileArtifact
from rlab.results.log import LogArtifact
from rlab.results.metric import Metric
from rlab.results.table import TableArtifact


def test_metric_and_artifact_models() -> None:
    metric = Metric(name="l2_error", value=0.003)
    assert metric.unit == "dimensionless"
    assert metric.direction == Direction.MINIMIZE
    assert metric.step is None
    assert TableArtifact(name="results", path=Path("tables/results.csv"), format="csv").format == "csv"
    assert "pdf" in FigureArtifact(name="loss_curve", path=Path("figures/loss.png"), formats=("png", "pdf")).formats
    assert FileArtifact(name="mesh", path=Path("artifacts/mesh.vtk"), media_type="model/vtk").media_type == "model/vtk"
    assert LogArtifact(name="solver", path=Path("logs/solver.log")).name == "solver"


def test_result_bundle_factories_merge_and_validation() -> None:
    assert empty_bundle().as_metrics_dict() == {}
    bundle = bundle_from_metrics({"accuracy": 0.92, "loss": 0.4})
    assert bundle.metric("accuracy").value == pytest.approx(0.92)

    merged = ResultBundle(metrics=(Metric(name="m1", value=1.0),)).merge(
        ResultBundle(metrics=(Metric(name="m2", value=2.0),))
    )
    assert merged.as_metrics_dict() == {"m1": 1.0, "m2": 2.0}

    with pytest.raises(ValueError, match="Duplicate"):
        ResultBundle(metrics=(Metric(name="loss", value=1.0), Metric(name="loss", value=2.0)))
