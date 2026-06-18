from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_cli_nested_run_uses_runtime_context_run(tmp_path: Path) -> None:
    _write_project(tmp_path)

    result = _run(tmp_path, "workflow:parent")

    parent_run = tmp_path / ".rlab" / "runs" / str(result["data"]["id"])
    child_entries = _jsonl(parent_run / "child_runs.jsonl")
    assert len(child_entries) == 1
    child_run = tmp_path / ".rlab" / "runs" / str(child_entries[0]["run_id"])
    assert child_entries[0]["status"] == "completed"
    assert (child_run / "artifacts" / "file" / "message.txt").read_text(
        encoding="utf-8"
    ) == "hello"

    parent_result = json.loads((parent_run / "results.json").read_text(encoding="utf-8"))
    parent_step = parent_result["data"]["steps"][0]["result"]
    assert parent_step == {
        "child_message": "hello",
        "child_score": 0.5,
        "child_status": "completed",
    }


def test_cli_nested_run_failure_modes(tmp_path: Path) -> None:
    _write_project(tmp_path)

    failed = _run_process(tmp_path, "workflow:parent_default_failure")
    assert failed.returncode == 1

    allowed = _run(tmp_path, "workflow:parent_allow_failure")
    parent_run = tmp_path / ".rlab" / "runs" / str(allowed["data"]["id"])
    parent_result = json.loads((parent_run / "results.json").read_text(encoding="utf-8"))
    assert parent_result["data"]["steps"][0]["result"] == {"child_status": "failed"}


def _run(root: Path, target: str) -> dict[str, object]:
    result = _run_process(root, target)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _run_process(root: Path, target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "rlab", "--root", str(root), "run", target, "--json"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_project(root: Path) -> None:
    (root / "lab.toml").write_text(
        """
schema_version = 1

[project]
name = "nested-test"

[paths]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
cache = ".rlab/cache"

[python]
modules = ["workflows"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    workflows = root / "workflows"
    workflows.mkdir()
    (workflows / "__init__.py").write_text(
        """
import rlab

lab = rlab.Project()

@lab.workflow("child", step="run")
def child(ctx):
    output = ctx.output_path("message.txt")
    output.write_text(ctx.str_param("message"), encoding="utf-8")
    ctx.log_metric("child.score", 0.5)
    ctx.save_file("message", output)
    return {"ok": True}

@lab.workflow("child_fail", step="run")
def child_fail(ctx):
    raise RuntimeError("planned child failure")

@lab.workflow("parent", step="run")
def parent(ctx):
    child = ctx.run("workflow:child", {"message": "hello"}, seed=7)
    return {
        "child_status": child.status,
        "child_score": child.metrics()["child.score"],
        "child_message": child.artifact("message").read_text(encoding="utf-8"),
    }

@lab.workflow("parent_default_failure", step="run")
def parent_default_failure(ctx):
    ctx.run("workflow:child_fail")

@lab.workflow("parent_allow_failure", step="run")
def parent_allow_failure(ctx):
    child = ctx.run("workflow:child_fail", allow_failure=True)
    return {"child_status": child.status}
""",
        encoding="utf-8",
    )


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
