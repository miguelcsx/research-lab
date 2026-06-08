from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS studies (
    name TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    domain TEXT NOT NULL DEFAULT 'general',
    decision_rule TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_runs (
    study TEXT NOT NULL,
    run_id TEXT NOT NULL,
    linked_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (study, run_id)
);
"""


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class StudyStore:
    """Persistent index of studies and their linked runs."""

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

    def upsert(
        self, name: str, question: str, *, domain: str = "general", decision_rule: str = ""
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO studies (name, question, domain, decision_rule, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (name, question, domain, decision_rule, _now()),
            )

    def link_run(self, study: str, run_id: str, *, notes: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO study_runs (study, run_id, linked_at, notes)"
                " VALUES (?, ?, ?, ?)",
                (study, run_id, _now(), notes),
            )

    def list(self) -> tuple[dict[str, str], ...]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM studies ORDER BY created_at DESC").fetchall()
        return tuple(dict(row) for row in rows)

    def runs_for(self, study: str) -> tuple[dict[str, str], ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM study_runs WHERE study = ? ORDER BY linked_at DESC",
                (study,),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def export(self) -> str:
        return json.dumps({"studies": list(self.list())}, indent=2)