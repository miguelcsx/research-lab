from pathlib import Path

from click.testing import Result
from pytest import MonkeyPatch
from typer.testing import CliRunner

from rlab.cli.app import app
from rlab.cli.commands import init as init_command
from rlab.cli.commands import run as run_command
from rlab.context.factory import build_runtime
from rlab.data.service import build
from rlab.evaluations.service import run_evaluation
from rlab.experiments.service import run_experiment

runner = CliRunner()


def invoke(project: Path, *args: str) -> Result:
    return runner.invoke(app, ["--root", str(project), *args])


def test_help_and_init(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        init_command,
        "lock_project",
        lambda project: (project / "uv.lock").write_text("version = 1\n"),
    )
    assert runner.invoke(app, ["--help"]).exit_code == 0
    result = runner.invoke(app, ["--root", str(tmp_path), "init", "project", "generated"])
    assert result.exit_code == 0
    assert (tmp_path / "generated" / "lab.toml").exists()
    assert (tmp_path / "generated" / "uv.lock").exists()
    for kind in ("plugin", "benchmark", "experiment", "suite"):
        result = runner.invoke(app, ["--root", str(tmp_path), "init", kind, f"{kind}_template"])
        assert result.exit_code == 0
    result = runner.invoke(app, ["--root", str(tmp_path), "init", "data-project", "data-project"])
    assert result.exit_code == 0


def test_core_commands(project: Path) -> None:
    assert invoke(project, "doctor").exit_code == 0
    assert invoke(project, "config", "validate").exit_code == 0
    assert invoke(project, "config", "show").exit_code == 0
    assert invoke(project, "config", "paths").exit_code == 0
    assert invoke(project, "discover").exit_code == 0
    assert invoke(project, "--json", "discover", "benchmarks").exit_code == 0
    assert (
        invoke(
            project,
            "run",
            str(project / "experiments" / "000_smoke.py"),
            "--dry-run",
        ).exit_code
        == 0
    )
    assert (
        invoke(
            project,
            "bench",
            "tokenizer:project.byte",
            "project.tokenizer.length",
            "--repeat",
            "2",
        ).exit_code
        == 0
    )
    assert (
        invoke(
            project,
            "eval",
            "project.quick",
            "--model",
            "model:project.constant",
        ).exit_code
        == 0
    )
    assert (
        invoke(
            project,
            "run",
            str(project / "experiments" / "000_smoke.py"),
        ).exit_code
        == 0
    )
    assert invoke(project, "status").exit_code == 0


def test_data_artifact_compare_report_and_reproduce(project: Path) -> None:
    runtime = build_runtime(project)
    data_run = build(runtime, "dataset:project.tiny")
    evaluation = run_evaluation(runtime, "project.quick", "model:project.constant")
    experiment = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    manifest = data_run / "artifacts" / "dataset" / "manifest.yaml"
    benchmark_output = project / "reports" / "benchmark-run"
    assert (
        invoke(
            project,
            "bench",
            "tokenizer:project.byte",
            "project.tokenizer.length",
            "--output",
            str(benchmark_output),
            "--compare-with",
            str(evaluation),
        ).exit_code
        == 0
    )
    assert benchmark_output.exists()
    assert invoke(project, "data", "profile", str(manifest)).exit_code == 0
    assert invoke(project, "data", "validate", str(manifest)).exit_code == 0
    assert invoke(project, "data", "diff", str(manifest), str(manifest)).exit_code == 0
    assert invoke(project, "data", "compare", str(manifest), str(manifest)).exit_code == 0
    assert (
        invoke(project, "data", "ablate", "dataset:x", "--factor", "enabled=true,false").exit_code
        == 0
    )
    assert invoke(project, "data", "sample", str(manifest), "--n", "1").exit_code == 0
    assert invoke(project, "data", "lineage", str(manifest)).exit_code == 0
    assert (
        invoke(
            project,
            "data",
            "promote",
            str(manifest),
            "--as",
            "project.tiny",
            "--alias",
            "candidate",
        ).exit_code
        == 0
    )
    assert invoke(project, "artifacts", "list").exit_code == 0
    assert (
        invoke(
            project,
            "artifacts",
            "pull",
            "artifact:dataset/project.tiny@candidate",
        ).exit_code
        == 0
    )
    reference = "artifact:dataset/project.tiny@1"
    assert (
        invoke(
            project,
            "artifacts",
            "describe",
            reference,
        ).exit_code
        == 0
    )
    assert invoke(project, "artifacts", "lineage", reference).exit_code == 0
    assert invoke(project, "artifacts", "deprecate", reference).exit_code == 0
    assert (
        invoke(
            project,
            "compare",
            "datasets",
            str(manifest),
            str(manifest),
        ).exit_code
        == 0
    )
    comparison = project / "reports" / "comparison.csv"
    assert (
        invoke(
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
            str(comparison),
        ).exit_code
        == 0
    )
    assert comparison.exists()
    assert invoke(project, "compare", str(project / "runs"), "--format", "json").exit_code == 0
    assert invoke(project, "report", "run", str(evaluation)).exit_code == 0
    assert invoke(project, "report", "compare", str(project / "runs")).exit_code == 0
    assert invoke(project, "lineage", str(experiment)).exit_code == 0
    assert invoke(project, "reproduce", str(experiment), "--dry-run").exit_code == 0
    assert invoke(project, "artifacts", "delete", reference).exit_code == 0


def test_plugin_cache_and_jobs_commands(project: Path) -> None:
    assert invoke(project, "plugins", "list").exit_code == 0
    assert invoke(project, "plugins", "entrypoints").exit_code == 0
    assert invoke(project, "plugins", "conflicts").exit_code == 0
    assert invoke(project, "plugins", "doctor").exit_code == 0
    assert invoke(project, "cache", "path").exit_code == 0
    assert invoke(project, "cache", "inspect").exit_code == 0
    assert invoke(project, "cache", "list").exit_code == 0
    started = invoke(project, "jobs", "start", "python -c 'print(1)'")
    assert started.exit_code == 0
    job_id = started.stdout.strip().splitlines()[-1]
    assert invoke(project, "jobs", "list").exit_code == 0
    assert invoke(project, "jobs", "logs", job_id).exit_code == 0
    assert invoke(project, "cache", "prune", "downloads").exit_code == 0


def test_cli_launch_and_validation_errors(
    project: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_command, "launch_run", lambda *_args, **_kwargs: "job-1")
    result = invoke(
        project,
        "run",
        str(project / "experiments" / "000_smoke.py"),
        "--launcher",
        "subprocess",
    )
    assert result.exit_code == 0
    assert "job-1" in result.stdout
    assert invoke(project, "plugins", "describe", "missing").exit_code != 0
    assert invoke(project, "artifacts", "push").exit_code != 0
