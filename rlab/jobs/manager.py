import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rlab.jobs.model import JobRecord, JobStatus
from rlab.jobs.process import cancel_pid, cancel_process, is_same_process, process_start, spawn
from rlab.jobs.store import JobStore

_REAP_TIMEOUT_SECONDS = 1.0


class JobManager:
    def __init__(self, store: JobStore, log_dir: Path) -> None:
        self.store = store
        self.log_dir = log_dir
        self._processes: dict[str, subprocess.Popen[bytes]] = {}

    def start(self, command: tuple[str, ...], cwd: Path) -> JobRecord:
        job_id = uuid4().hex[:12]
        log = self.log_dir / f"{job_id}.log"
        process = spawn(command, cwd, log)
        self._processes[job_id] = process
        status = JobStatus.RUNNING
        # If the process already finished, reap it immediately.
        if process.poll() is not None:
            self._reap_process(job_id)
            status = JobStatus.STALE
        job = JobRecord(
            id=job_id,
            pid=process.pid,
            process_start=process_start(process.pid),
            command=command,
            cwd=cwd,
            log=log,
            status=status,
            created_at=datetime.now(UTC),
        )
        self.store.put(job)
        return job

    def refresh(self, job: JobRecord) -> JobRecord:
        if job.status is not JobStatus.RUNNING:
            return job
        if job.id in self._processes:
            process = self._processes[job.id]
            if process.poll() is None:
                return job
            self._reap_process(job.id)
            updated = job.model_copy(update={"status": JobStatus.STALE})
            self.store.put(updated)
            return updated
        if is_same_process(job.pid, job.process_start):
            return job
        updated = job.model_copy(update={"status": JobStatus.STALE})
        self.store.put(updated)
        return updated

    def cancel(self, job_id: str) -> JobRecord:
        job = self.store.get(job_id)
        if job_id in self._processes:
            process = self._processes[job_id]
            if process.poll() is None:
                cancel_process(process)
            self._reap_process(job_id)
            updated = job.model_copy(update={"status": JobStatus.CANCELLED})
        elif is_same_process(job.pid, job.process_start):
            cancel_pid(job.pid)
            updated = job.model_copy(update={"status": JobStatus.CANCELLED})
        else:
            updated = job.model_copy(update={"status": JobStatus.STALE})
        self.store.put(updated)
        return updated

    def _reap_process(self, job_id: str) -> None:
        process = self._processes.pop(job_id, None)
        if process is not None:
            try:
                process.wait(timeout=_REAP_TIMEOUT_SECONDS)
            except (OSError, subprocess.SubprocessError):
                process.kill()
                process.wait()

    def __del__(self) -> None:
        for job_id in list(self._processes):
            self._reap_process(job_id)
