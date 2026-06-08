from __future__ import annotations

import json
from pathlib import Path

from rlab.artifacts.lineage import ArtifactLineageGraph
from rlab.context.factory import build_runtime
from rlab.experiments.service import run_experiment
from rlab.graph.store import KnowledgeGraph
from rlab.runs.layout import RunLayout
from rlab.runs.writer import RunWriter
from tests.helpers.cli import assert_failure, assert_success, invoke_cli
from tests.helpers.files import inject_module_load


def test_notes_search_journal_and_ideas(project: Path) -> None:
    run_path = run_experiment(build_runtime(project), project / "experiments" / "000_smoke.py")
    assert isinstance(run_path, Path)

    assert_success(invoke_cli(project, "notes", "add", run_path.name, "This is a test note"))
    assert_success(invoke_cli(project, "notes", "list", run_path.name), "test note")
    assert_success(invoke_cli(project, "search", "unique_xyz_no_match_term"))
    assert_success(invoke_cli(project, "search", "smoke"))

    assert_success(
        invoke_cli(project, "journal", "decision", "add", "Promote model_v3 based on accuracy")
    )
    assert_success(invoke_cli(project, "journal", "decision", "list"), "Promote")
    assert_success(
        invoke_cli(
            project, "journal", "negative", "add", "dedup helps", "tried minhash", "no improvement"
        )
    )
    assert_success(invoke_cli(project, "journal", "negative", "list"))
    assert_success(invoke_cli(project, "journal", "negative", "search", "minhash"))
    assert_success(invoke_cli(project, "journal", "ideas", "add", "Try balanced data mixing"))
    assert_success(invoke_cli(project, "journal", "ideas", "list", "--status", "idea"))


def test_baseline_graph_invalidation_and_impact(project: Path) -> None:
    lineage = ArtifactLineageGraph(project / ".rlab" / "lineage.db")
    lineage.add_edge("dataset:test", "model:v1")
    lineage.add_edge("dataset:raw_v1", "model:best_v1")
    lineage.add_edge("model:best_v1", "report:final")

    assert_success(
        invoke_cli(
            project,
            "baselines",
            "add",
            "gpt2_base",
            "--metric",
            "accuracy",
            "--value",
            "0.85",
            "--description",
            "GPT-2 baseline",
        )
    )
    assert_success(invoke_cli(project, "baselines", "list"), "gpt2_base")

    assert_success(invoke_cli(project, "graph", "build"))
    assert_success(invoke_cli(project, "graph", "query", "SELECT * FROM graph_nodes LIMIT 5"))
    assert_success(invoke_cli(project, "graph", "lineage", "run:nonexistent"))
    assert_success(invoke_cli(project, "impact", "dataset:raw_v1"))
    assert_success(
        invoke_cli(project, "invalidate", "dataset:test", "--reason", "test contamination")
    )


def test_graph_lineage_depth_command(project: Path) -> None:
    graph = KnowledgeGraph(project / ".rlab" / "graph.db")
    graph.add_node("raw:data", "dataset", "Raw Data")
    graph.add_node("clean:v1", "dataset", "Clean V1")
    graph.add_edge("raw:data", "clean:v1", "produced")

    assert_success(invoke_cli(project, "graph", "lineage", "raw:data", "--depth", "5"))


def test_lint_ci_freeze_plan_exec_diff_and_handoff(project: Path) -> None:
    runtime = build_runtime(project)
    run_a = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(run_a, Path)
    run_b = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(run_b, Path)
    RunWriter(RunLayout(root=run_a)).params({"lr": 0.001, "model": "tiny"})
    RunWriter(RunLayout(root=run_b)).params({"lr": 0.01, "model": "small"})

    assert invoke_cli(project, "lint").exit_code in (0, 1)
    assert_success(invoke_cli(project, "ci", "smoke"))
    assert_success(invoke_cli(project, "ci", "reproducibility-check"))
    assert_success(invoke_cli(project, "freeze", "run", str(run_a), "--as", "paper_run"))
    assert_success(invoke_cli(project, "freeze", "lock", str(run_a)))
    assert_success(invoke_cli(project, "freeze", "export", str(run_a), "--format", "repro-zip"))
    assert_success(invoke_cli(project, "freeze", "methods", str(run_a)))
    assert_success(
        invoke_cli(project, "plan", "power", "--effect-size", "0.1", "--variance", "1.0")
    )
    assert_success(
        invoke_cli(
            project,
            "plan",
            "cost",
            str(project / "experiments" / "000_smoke.py"),
            "--seconds-per-job",
            "60",
        )
    )
    assert_success(invoke_cli(project, "exec", "--name", "echo_test", "echo", "42"))
    assert_failure(invoke_cli(project, "exec", "--name", "fail_cmd", "false"))
    assert_success(
        invoke_cli(
            project,
            "exec",
            "--name",
            "cmd_with_parser",
            "--parser",
            "rlab.nonexistent:parse",
            "echo",
            "42",
        )
    )
    assert_success(invoke_cli(project, "diff", str(run_a), str(run_b)))
    assert_success(invoke_cli(project, "handoff", run_a.name, "--to", "team-b"))
    assert (run_a / "handoff.md").exists()


def test_ci_compare_detects_regression(project: Path) -> None:
    runtime = build_runtime(project)
    baseline = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(baseline, Path)
    candidate = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(candidate, Path)
    RunWriter(RunLayout(root=baseline)).metric("test_metric", 0.9)
    RunWriter(RunLayout(root=candidate)).metric("test_metric", 0.5)

    assert_failure(
        invoke_cli(
            project,
            "ci",
            "compare",
            "--baseline",
            baseline.name,
            "--candidate",
            candidate.name,
            "--metric",
            "test_metric",
            "--threshold",
            "0.001",
        )
    )


def test_ci_reproducibility_check_fails_on_dirty_run(project: Path) -> None:
    run_path = run_experiment(build_runtime(project), project / "experiments" / "000_smoke.py")
    assert isinstance(run_path, Path)
    repro_dir = run_path / "reproducibility"
    repro_dir.mkdir(exist_ok=True)
    (repro_dir / "git.json").write_text(json.dumps({"dirty": True}), encoding="utf-8")

    assert_failure(invoke_cli(project, "ci", "reproducibility-check"))


def test_modules_doctor_reports_failed_module(basic_project: Path) -> None:
    inject_module_load(basic_project, "broken_module_xyz")
    assert_failure(invoke_cli(basic_project, "modules", "doctor"))


def test_ci_smoke_reports_failed_module(basic_project: Path) -> None:
    inject_module_load(basic_project, "broken.module_xyz")
    assert_failure(invoke_cli(basic_project, "ci", "smoke"))
