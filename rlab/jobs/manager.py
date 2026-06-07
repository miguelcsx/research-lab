from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rlab.jobs.model import JobRecord, JobStatus
from rlab.jobs.process import cancel, is_same_process, process_start, spawn
from rlab.jobs.store import JobStore


class JobManager:
    def __init__(self, store: JobStore, log_dir: Path) -> None:
        self.store = store
        self.log_dir = log_dir

    def start(self, command: tuple[str, ...], cwd: Path) -> JobRecord:
        job_id = uuid4().hex[:12]
        log = self.log_dir / f"{job_id}.log"
        process = spawn(command, cwd, log)
        job = JobRecord(
            id=job_id,
            pid=process.pid,
            process_start=process_start(process.pid),
            command=command,
            cwd=cwd,
            log=log,
            status=JobStatus.RUNNING,
            created_at=datetime.now(UTC),
        )
        self.store.put(job)
        return job

    def refresh(self, job: JobRecord) -> JobRecord:
        if job.status is not JobStatus.RUNNING:
            return job
        if is_same_process(job.pid, job.process_start):
            return job
        updated = job.model_copy(update={"status": JobStatus.STALE})
        self.store.put(updated)
        return updated

    def cancel(self, job_id: str) -> JobRecord:
        job = self.store.get(job_id)
        if not is_same_process(job.pid, job.process_start):
            updated = job.model_copy(update={"status": JobStatus.STALE})
        else:
            cancel(job.pid)
            updated = job.model_copy(update={"status": JobStatus.CANCELLED})
        self.store.put(updated)
        return updated
