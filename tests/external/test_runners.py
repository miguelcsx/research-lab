import json
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


def test_external_runners_and_parsers(tmp_path: Path) -> None:
    result = ShellRunner().run(
        ExternalCommand(args=("python", "-c", "print('ok')"), cwd=tmp_path),
        tmp_path,
    )
    assert result.stdout.strip() == "ok"
    with pytest.raises(ExternalRunError):
        ShellRunner().run(
            ExternalCommand(args=("python", "-c", "raise SystemExit(2)")),
            tmp_path,
        )
    with pytest.raises(subprocess.TimeoutExpired):
        ShellRunner().run(
            ExternalCommand(
                args=("python", "-c", "import time; time.sleep(1)"),
                timeout_seconds=0,
            ),
            tmp_path,
        )
    output = tmp_path / "metrics.json"
    output.write_text(json.dumps({"score": 1, "ignored": "x"}))
    assert json_metrics(output) == {"score": 1.0}
    output.write_text("[]")
    with pytest.raises(ValueError):
        json_metrics(output)
    output.write_text('{"ignored":"x"}')
    with pytest.raises(ValueError):
        json_metrics(output)


def test_command_factories_and_sandbox(tmp_path: Path) -> None:
    assert PythonModuleRunner().command("module").args[:3] == ("python", "-m", "module")
    assert UvRunner().command("tool").args[:2] == ("uv", "run")
    assert CondaRunner().command("env", "tool").args[:4] == ("conda", "run", "-n", "env")
    docker = DockerRunner().command("image", "tool", mounts=((tmp_path, "/data"),))
    assert docker.args[0:3] == ("docker", "run", "--rm")
    assert sandbox_environment({"X": "1"})["X"] == "1"
    assert safe_workdir(tmp_path, None) == tmp_path
    with pytest.raises(ValueError):
        safe_workdir(tmp_path, tmp_path / "missing")
    assert external_cache(tmp_path, "repo", "rev") == tmp_path / "external" / "repo" / "rev"


def test_repository_checkout(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(("git", "init"), cwd=source, check=True, capture_output=True)
    subprocess.run(("git", "config", "user.email", "test@example.com"), cwd=source, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=source, check=True)
    (source / "file").write_text("value")
    subprocess.run(("git", "add", "file"), cwd=source, check=True)
    subprocess.run(
        ("git", "-c", "commit.gpgsign=false", "commit", "-m", "initial"),
        cwd=source,
        check=True,
        capture_output=True,
    )
    revision = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=source,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    checkout = checkout_repository(str(source), revision, tmp_path / "cache")
    assert (checkout / "file").read_text() == "value"
    assert checkout_repository(str(source), revision, tmp_path / "cache") == checkout
    with pytest.raises(ExternalRunError):
        checkout_repository(str(tmp_path / "missing"), revision, tmp_path / "bad")
