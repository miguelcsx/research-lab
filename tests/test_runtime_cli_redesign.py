from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_discover_groups_runtime_entries_and_run_rejects_support(tmp_path: Path) -> None:
    _write_project(tmp_path)

    discovered = _cli(tmp_path, "discover")
    assert discovered.returncode == 0, discovered.stderr
    assert "Runnable" in discovered.stdout
    assert "experiment:train" in discovered.stdout
    assert "Support" in discovered.stdout
    assert "loader:weights" in discovered.stdout

    run = _cli(
        tmp_path,
        "run",
        "experiment:train",
        "--json",
        "--param",
        "width=7",
    )
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    run_dir = tmp_path / ".rlab" / "runs" / str(payload["data"]["id"])
    result = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert result["data"] == {"width": 7}

    support = _cli(tmp_path, "run", "loader:weights", "--json")
    assert support.returncode == 1
    assert "not a runnable target" in support.stderr


def _cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "rlab", "--root", str(root), *args],
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
name = "runtime-cli-test"

[paths]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
cache = ".rlab/cache"

[python]
modules = ["experiments"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    experiments = root / "experiments"
    experiments.mkdir()
    (experiments / "__init__.py").write_text(
        """
from dataclasses import dataclass

import rlab

lab = rlab.Project()

@dataclass
class Params:
    width: int

@lab.experiment("train", params=Params)
def train(ctx):
    params = ctx.params(Params)
    return {"width": params.width}

@lab.loader("weights")
def weights(ctx):
    return {"path": "weights.bin"}
""",
        encoding="utf-8",
    )
