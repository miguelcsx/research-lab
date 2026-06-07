import json
import sqlite3
from pathlib import Path

from rlab.jobs.model import JobRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
)
"""


class JobStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as connection:
            connection.execute(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def put(self, job: JobRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?, ?)",
                (job.id, job.model_dump_json()),
            )

    def get(self, job_id: str) -> JobRecord:
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return JobRecord.model_validate(json.loads(row[0]))

    def list(self) -> tuple[JobRecord, ...]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM jobs ORDER BY id DESC").fetchall()
        return tuple(JobRecord.model_validate_json(row[0]) for row in rows)
