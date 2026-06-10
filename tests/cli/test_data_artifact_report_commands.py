from __future__ import annotations

import json
from pathlib import Path

from rlab.context.factory import build_runtime
from rlab.data.service import build
from rlab.evaluations.service import run_evaluation
from rlab.experiments.service import run_experiment
from tests.helpers.cli import assert_success, invoke_cli


def test_data_build_records_param_overrides(project: Path) -> None:
    assert_success(
        invoke_cli(
            project,
            "data",
            "build",
            "dataset:project.tiny",
            "--override",
            "source.limit=1",
        )
    )

    run_dirs = sorted((project / "runs").glob("data.build_*"))
    assert run_dirs, "expected a data build run directory"
    params = json.loads((run_dirs[-1] / "params.json").read_text())
    assert params["source.limit"] == 1


def test_data_artifacts_compare_report_and_reproduce(project: Path) -> None:
    runtime = build_runtime(project)
    data_run = build(runtime, "dataset:project.tiny")
    evaluation = run_evaluation(runtime, "project.quick", "model:project.constant")
    experiment = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    manifest = data_run / "artifacts" / "dataset" / "manifest.yaml"
    benchmark_output = project / "reports" / "benchmark-run"

    assert_success(
        invoke_cli(
            project,
            "bench",
            "tokenizer:project.byte",
            "project.tokenizer.length",
            "--output",
            str(benchmark_output),
            "--compare-with",
            str(evaluation),
        )
    )
    assert benchmark_output.exists()

    for args in (
        ("data", "profile", str(manifest)),
        ("data", "validate", str(manifest)),
        ("data", "diff", str(manifest), str(manifest)),
        ("data", "compare", str(manifest), str(manifest)),
        ("data", "sample", str(manifest), "--n", "1"),
        ("data", "lineage", str(manifest)),
        ("data", "audit", str(data_run)),
        ("data", "reasons", str(data_run)),
        ("data", "stage-summary", str(data_run)),
        ("data", "source-summary", str(data_run)),
        ("artifacts", "list"),
        ("compare", "datasets", str(manifest), str(manifest)),
        ("report", "run", str(evaluation)),
        ("report", "compare", str(project / "runs")),
        ("lineage", str(experiment)),
        ("reproduce", str(experiment), "--dry-run"),
    ):
        assert_success(invoke_cli(project, *args))

    missing_samples = invoke_cli(project, "data", "sample-drops", str(data_run), "empty")
    assert missing_samples.exit_code != 0
    assert "No audit samples captured" in missing_samples.output
    assert "Traceback" not in missing_samples.output

    assert_success(
        invoke_cli(project, "data", "ablate", "dataset:x", "--factor", "enabled=true,false")
    )
    assert_success(
        invoke_cli(
            project,
            "data",
            "promote",
            str(manifest),
            "--as",
            "project.tiny",
            "--alias",
            "candidate",
        )
    )
    assert_success(
        invoke_cli(project, "artifacts", "pull", "artifact:dataset/project.tiny@candidate")
    )

    reference = "artifact:dataset/project.tiny@1.0.0"
    for args in (
        ("artifacts", "describe", reference),
        ("artifacts", "lineage", reference),
        ("artifacts", "deprecate", reference),
        ("artifacts", "delete", reference),
    ):
        assert_success(invoke_cli(project, *args))


def test_compare_runs_can_write_csv_and_json(project: Path) -> None:
    runtime = build_runtime(project)
    evaluation = run_evaluation(runtime, "project.quick", "model:project.constant")
    output = project / "reports" / "comparison.csv"

    assert_success(
        invoke_cli(
            project,
            "compare",
            str(project / "runs"),
            "--metric",
            "score.score",
            "--group-by",
            "operation",
            "--sort-by",
            "score.score",
            "--baseline",
            evaluation.name,
            "--format",
            "csv",
            "--output",
            str(output),
        )
    )
    assert output.exists()
    assert_success(invoke_cli(project, "compare", str(project / "runs"), "--format", "json"))
