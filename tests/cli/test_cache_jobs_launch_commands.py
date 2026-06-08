from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from rich.console import Console

from rlab.cli.commands import run as run_command
from rlab.cli.launch import launch_run
from rlab.cli.state import CliState
from rlab.jobs.manager import JobManager
from rlab.jobs.model import JobRecord, JobStatus
from tests.helpers.cli import assert_failure, assert_success, invoke_cli


def test_cache_and_job_commands(project: Path) -> None:
    for args in (("cache", "path"), ("cache", "inspect"), ("cache", "list")):
        assert_success(invoke_cli(project, *args))

    started = assert_success(invoke_cli(project, "jobs", "start", "python -c 'print(1)'"))
    job_id = started.stdout.strip().splitlines()[-1]
    assert_success(invoke_cli(project, "jobs", "list"))
    assert_success(invoke_cli(project, "jobs", "logs", job_id))
    assert_success(invoke_cli(project, "cache", "prune", "downloads"))


def test_run_command_can_launch_in_subprocess_mode(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_command, "launch_run", lambda *_args, **_kwargs: "job-1")

    result = assert_success(
        invoke_cli(
            project,
            "run",
            str(project / "experiments" / "000_smoke.py"),
            "--launcher",
            "subprocess",
        )
    )
    assert "job-1" in result.stdout


def test_artifacts_push_requires_input(project: Path) -> None:
    assert_failure(invoke_cli(project, "artifacts", "push"))


def test_launch_subprocess_builds_expected_command(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def start(_self: JobManager, command: tuple[str, ...], cwd: Path) -> JobRecord:
        captured.update(command=command, cwd=cwd)
        return JobRecord(
            id="job-1",
            pid=1,
            process_start="1",
            command=command,
            cwd=cwd,
            log=project / "job.log",
            status=JobStatus.RUNNING,
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(JobManager, "start", start)
    job_id = launch_run(
        CliState(root=project, console=Console()),
        "subprocess",
        project / "experiments" / "000_smoke.py",
        only="job-0",
    )

    assert job_id == "job-1"
    assert captured["cwd"] == project
    assert "--only" in captured["command"]  # type: ignore[operator]


def test_launch_validates_launcher_configuration(project: Path) -> None:
    state = CliState(root=project, console=Console())
    experiment = project / "experiments" / "000_smoke.py"
    with pytest.raises(ValueError, match="docker_image"):
        launch_run(state, "docker", experiment, only=None)
    with pytest.raises(ValueError, match="Unsupported launcher"):
        launch_run(state, "cluster", experiment, only=None)
