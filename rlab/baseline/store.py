import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from rlab.baseline.model import BaselineEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS baselines (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    run_id TEXT,
    metric TEXT NOT NULL DEFAULT '',
    value REAL,
    description TEXT NOT NULL DEFAULT '',
    for_project TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


class BaselineStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def add(self, entry: BaselineEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO baselines
                   (
                       name, kind, run_id, metric, value,
                       description, for_project, source, tags, created_at
                   )
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.name,
                    entry.kind,
                    entry.run_id,
                    entry.metric,
                    entry.value,
                    entry.description,
                    entry.for_project,
                    entry.source,
                    json.dumps(list(entry.tags)),
                    datetime.now(tz=UTC).isoformat(),
                ),
            )

    def get(self, name: str) -> BaselineEntry | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM baselines WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["tags"] = tuple(json.loads(d["tags"]))
        return BaselineEntry(**{k: v for k, v in d.items() if k != "created_at"})

    def list(self, *, for_project: str | None = None) -> tuple[BaselineEntry, ...]:
        with self._connect() as conn:
            if for_project:
                rows = conn.execute(
                    "SELECT * FROM baselines WHERE for_project = ?", (for_project,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM baselines").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["tags"] = tuple(json.loads(d["tags"]))
            result.append(BaselineEntry(**{k: v for k, v in d.items() if k != "created_at"}))
        return tuple(result)