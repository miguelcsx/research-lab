"""Simple job record models used by the Python facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

JobStatus = Literal["running", "completed", "failed", "cancelled"]


@dataclass(slots=True)
class JobRecord:
    id: str
    command: str
    status: JobStatus
    log_path: Path
    exit_code: int | None = None


__all__ = ["JobRecord", "JobStatus"]
