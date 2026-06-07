from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class JobRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    pid: int
    process_start: str
    command: tuple[str, ...]
    cwd: Path
    log: Path
    status: JobStatus
    created_at: datetime
    returncode: int | None = None
