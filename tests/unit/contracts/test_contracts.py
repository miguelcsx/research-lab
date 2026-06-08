from __future__ import annotations

from pathlib import Path

from rlab.contracts.component import ComponentContract, validate_compatibility
from rlab.contracts.manifest import validate_manifest
from rlab.contracts.result import ResultContract, validate_bundle
from rlab.results.bundle import ResultBundle
from rlab.results.figure import FigureArtifact
from rlab.results.metric import Metric
from rlab.results.table import TableArtifact


def test_component_contract_compatibility() -> None:
    upstream = ComponentContract(input_type="any", output_type="tensor")
    compatible = ComponentContract(input_type="tensor", output_type="float")
    incompatible = ComponentContract(input_type="mesh", output_type="float")

    assert validate_compatibility(compatible, upstream) == []
    issues = validate_compatibility(incompatible, upstream)
    assert len(issues) == 1
    assert "mismatch" in issues[0].lower()


def test_result_contract_validates_required_artifacts() -> None:
    bundle = ResultBundle(
        metrics=(Metric(name="accuracy", value=0.9),),
        figures=(FigureArtifact(name="loss_curve", path=Path("f.png")),),
        tables=(TableArtifact(name="results", path=Path("r.csv")),),
    )
    contract = ResultContract(
        required_metrics=("accuracy",),
        required_figures=("loss_curve",),
        required_tables=("results",),
    )
    assert validate_bundle(bundle, contract) == ()

    violations = validate_bundle(
        ResultBundle(), ResultContract(required_metrics=("accuracy", "f1"))
    )
    assert len(violations) == 1
    assert violations[0].field == "metrics"
    assert set(violations[0].missing) == {"accuracy", "f1"}


def test_manifest_contract_validation(tmp_path: Path) -> None:
    valid = tmp_path / "dataset.yaml"
    valid.write_text("kind: dataset\nname: babylm\nversion: 1.0\n", encoding="utf-8")
    assert validate_manifest(valid) == ()

    missing_version = tmp_path / "missing_version.yaml"
    missing_version.write_text("kind: dataset\nname: babylm\n", encoding="utf-8")
    assert any("version" in str(error) for error in validate_manifest(missing_version))
    assert "not found" in str(validate_manifest(tmp_path / "missing.yaml")[0])
