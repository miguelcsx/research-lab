from __future__ import annotations

from pathlib import Path

import pytest

from rlab import JobRecord
from rlab.jobs import JobRecord as ModuleJobRecord


def test_job_record_is_rust_backed(tmp_path: Path) -> None:
    record = JobRecord(
        "job-1",
        "echo ok",
        "completed",
        tmp_path / "job.log",
        exit_code=0,
    )

    assert record.id == "job-1"
    assert record.command == "echo ok"
    assert record.status == "completed"
    assert record.log_path == tmp_path / "job.log"
    assert record.exit_code == 0
    assert ModuleJobRecord("job-2", "echo ok", "running", tmp_path / "run.log").exit_code is None


def test_job_record_validates_in_rust(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        JobRecord("", "echo ok", "completed", tmp_path / "job.log")
    with pytest.raises(ValueError):
        JobRecord("job-1", "", "completed", tmp_path / "job.log")
    with pytest.raises(ValueError):
        JobRecord("job-1", "echo ok", "waiting", tmp_path / "job.log")  # type: ignore[arg-type]
