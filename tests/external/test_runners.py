from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from rlab.errors import ExternalRunError
from rlab.external.cache import external_cache
from rlab.external.command import ExternalCommand
from rlab.external.parser import json_metrics
from rlab.external.repo import checkout_repository
from rlab.external.runner import (
    CondaRunner,
    DockerRunner,
    PythonModuleRunner,
    ShellRunner,
    UvRunner,
)
from rlab.external.sandbox import safe_workdir, sandbox_environment
from tests.helpers.factories import create_git_repository


def test_shell_runner_returns_stdout_and_raises_on_failure(tmp_path: Path) -> None:
    runner = ShellRunner()
    result = runner.run(
        ExternalCommand(args=("python", "-c", "print('ok')"), cwd=tmp_path), tmp_path
    )
    assert result.stdout.strip() == "ok"

    with pytest.raises(ExternalRunError):
        runner.run(
            ExternalCommand(args=("python", "-c", "raise SystemExit(2)"), cwd=tmp_path), tmp_path
        )


def test_shell_runner_honors_timeout(tmp_path: Path) -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        ShellRunner().run(
            ExternalCommand(args=("python", "-c", "import time; time.sleep(1)"), timeout_seconds=0),
            tmp_path,
        )


def test_json_metrics_parser_accepts_numeric_fields_only(tmp_path: Path) -> None:
    output = tmp_path / "metrics.json"
    output.write_text(json.dumps({"score": 1, "ignored": "x"}), encoding="utf-8")
    assert json_metrics(output) == {"score": 1.0}

    for invalid in ([], {"ignored": "x"}):  # type: ignore[var-annotated]
        output.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError):
            json_metrics(output)


def test_command_factories_and_sandbox_helpers(tmp_path: Path) -> None:
    assert PythonModuleRunner().command("module").args[:3] == ("python", "-m", "module")
    assert UvRunner().command("tool").args[:2] == ("uv", "run")
    assert CondaRunner().command("env", "tool").args[:4] == ("conda", "run", "-n", "env")
    assert DockerRunner().command("image", "tool", mounts=((tmp_path, "/data"),)).args[:3] == (
        "docker",
        "run",
        "--rm",
    )
    assert sandbox_environment({"X": "1"})["X"] == "1"
    assert safe_workdir(tmp_path, None) == tmp_path
    with pytest.raises(ValueError):
        safe_workdir(tmp_path, tmp_path / "missing")
    assert external_cache(tmp_path, "repo", "rev") == tmp_path / "external" / "repo" / "rev"


@pytest.mark.skipif(
    shutil.which("git") is None, reason="git is required for repository checkout tests"
)
def test_repository_checkout_is_cached(tmp_path: Path) -> None:
    source, revision = create_git_repository(tmp_path / "source")
    checkout = checkout_repository(str(source), revision, tmp_path / "cache")

    assert (checkout / "file.txt").read_text(encoding="utf-8") == "value"
    assert checkout_repository(str(source), revision, tmp_path / "cache") == checkout
    with pytest.raises(ExternalRunError):
        checkout_repository(str(tmp_path / "missing"), revision, tmp_path / "bad")
