from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from rich.console import Console

from rlab.cli.launch import launch_run
from rlab.cli.state import CliState
from rlab.jobs.manager import JobManager
from rlab.jobs.model import JobRecord, JobStatus


def state(project: Path) -> CliState:
    return CliState(root=project, console=Console())


def test_launch_subprocess(
    project: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def start(
        _self: JobManager,
        command: tuple[str, ...],
        cwd: Path,
    ) -> JobRecord:
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
        state(project),
        "subprocess",
        project / "experiments" / "000_smoke.py",
        only="job-0",
    )

    assert job_id == "job-1"
    assert captured["cwd"] == project
    command = captured["command"]
    assert isinstance(command, tuple)
    assert "--only" in command


def test_launch_docker_requires_image(project: Path) -> None:
    with pytest.raises(ValueError, match="docker_image"):
        launch_run(
            state(project),
            "docker",
            project / "experiments" / "000_smoke.py",
            only=None,
        )


def test_launch_rejects_unknown_launcher(project: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported launcher"):
        launch_run(
            state(project),
            "cluster",
            project / "experiments" / "000_smoke.py",
            only=None,
        )
