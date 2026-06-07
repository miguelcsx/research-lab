import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rlab.constants import RunStatus
from rlab.errors import ConfigError
from rlab.jobs.manager import JobManager
from rlab.jobs.model import JobStatus
from rlab.jobs.process import is_same_process, process_start
from rlab.jobs.store import JobStore
from rlab.manifests.run import RunManifest
from rlab.runs.index import RunIndex
from rlab.tracking.local import LocalTracking
from rlab.tracking.null import NullTracking
from rlab.tracking.router import tracking_backend


def test_tracking_backends(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    manifest = RunManifest(
        kind="run",
        name="test",
        version="1",
        operation="test",
        status=RunStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )
    local = LocalTracking(RunIndex(tmp_path / "index.sqlite3"), tmp_path / "runs")
    local.start(manifest)
    local.metric("test", "score", 1.0)
    local.finish(manifest)
    assert tracking_backend("local", tmp_path, tmp_path / "runs")
    assert tracking_backend("null", tmp_path, tmp_path / "runs")
    null = NullTracking()
    null.start(manifest)
    null.metric("test", "x", 1)
    null.finish(manifest)
    with pytest.raises(ConfigError):
        tracking_backend("remote", tmp_path, tmp_path / "runs")


def test_job_store_and_manager(tmp_path: Path) -> None:
    manager = JobManager(JobStore(tmp_path / "jobs.sqlite3"), tmp_path / "logs")
    job = manager.start(("python", "-c", "import time; time.sleep(30)"), tmp_path)
    assert job.status is JobStatus.RUNNING
    assert process_start(job.pid)
    assert is_same_process(job.pid, job.process_start)
    assert manager.refresh(job).status is JobStatus.RUNNING
    cancelled = manager.cancel(job.id)
    assert cancelled.status is JobStatus.CANCELLED
    time.sleep(0.05)
    stale = manager.refresh(job.model_copy(update={"process_start": "wrong"}))
    assert stale.status is JobStatus.STALE
    assert manager.refresh(cancelled) is cancelled
    with pytest.raises(KeyError):
        manager.store.get("missing")
