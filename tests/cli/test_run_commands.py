from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rlab.runs.layout import RunLayout
from rlab.runs.lifecycle import fail_run, start_run
from rlab.runs.writer import RunWriter
from tests.helpers.cli import assert_failure, assert_success, invoke_cli, invoke_json
from tests.helpers.factories import run_smoke_experiment


def test_run_bench_and_eval_commands(project: Path) -> None:
    assert_success(
        invoke_cli(project, "run", str(project / "experiments" / "000_smoke.py"), "--dry-run")
    )
    assert_success(
        invoke_cli(
            project, "bench", "tokenizer:project.byte", "project.tokenizer.length", "--repeat", "2"
        )
    )
    assert_success(
        invoke_cli(project, "eval", "project.quick", "--model", "model:project.constant")
    )
    assert_success(invoke_cli(project, "run", str(project / "experiments" / "000_smoke.py")))


def test_runs_list_show_logs_and_query(project: Path) -> None:
    run_path = run_smoke_experiment(project)
    log_file = run_path / "logs" / "test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("Test log content\n", encoding="utf-8")

    assert_success(invoke_cli(project, "runs", "list"))
    assert_success(invoke_json(project, "runs", "list"))
    assert_success(invoke_cli(project, "runs", "list", "--status", "completed"))
    assert_success(invoke_cli(project, "runs", "list", "--limit", "5"))
    assert_success(invoke_cli(project, "runs", "show", run_path.name))
    assert_success(invoke_cli(project, "runs", "logs", run_path.name), "Test log content")
    assert_success(invoke_cli(project, "runs", "query", "status = 'completed'"))


def test_runs_show_and_logs_fail_for_unknown_run(project: Path) -> None:
    assert_failure(invoke_cli(project, "runs", "show", "missing_run"))
    assert_failure(invoke_cli(project, "runs", "logs", "missing_run"))


def test_runs_clean_dry_run_and_delete(project: Path) -> None:
    assert_success(invoke_cli(project, "runs", "clean", "--failed", "--dry-run"))
    run_path = run_smoke_experiment(project)
    start_run(run_path)
    fail_run(run_path, "test failure")

    assert_success(invoke_cli(project, "runs", "clean", "--failed"))
    assert not run_path.exists()


def test_runs_clean_without_runs_directory(basic_project: Path) -> None:
    assert_success(invoke_cli(basic_project, "runs", "clean", "--failed"))


def test_runs_query_rejects_invalid_sql(project: Path) -> None:
    assert_failure(invoke_cli(project, "runs", "query", "INVALID SQL SYNTAX !!!"))


def test_runs_tail_stops_cleanly(project: Path) -> None:
    run_path = run_smoke_experiment(project)
    RunWriter(RunLayout(root=run_path)).metric("live_metric", 0.5)

    def stop_after_first_sleep(_seconds: float) -> None:
        raise KeyboardInterrupt

    with patch("rlab.cli.commands.runs.time.sleep", stop_after_first_sleep):
        assert_success(invoke_cli(project, "runs", "tail", run_path.name))


def test_runs_show_handles_corrupt_manifest(project: Path) -> None:
    run_path = run_smoke_experiment(project)
    (run_path / "run.yaml").write_text("invalid: yaml: content:", encoding="utf-8")
    result = invoke_cli(project, "runs", "show", run_path.name)
    assert result.exit_code in (0, 1)
