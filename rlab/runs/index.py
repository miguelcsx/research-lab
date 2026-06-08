from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rlab.constants import RunStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT,
    parent_id TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    params TEXT NOT NULL DEFAULT '{}'
);
"""


_ALLOWED_PREFIXES = ("select", "with")


def _ensure_select(sql: str) -> None:
    stripped = sql.lstrip().lower()
    if not any(stripped.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
        raise ValueError("Only SELECT/WITH queries are permitted")


def _decode_json_field(value: str) -> Any:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


class RunIndex:
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

    def upsert(  # noqa: PLR0913
        self,
        *,
        run_id: str,
        name: str,
        operation: str,
        status: RunStatus | str,
        path: Path,
        created_at: str | None = None,
        parent_id: str | None = None,
        tags: tuple[str, ...] = (),
        params: dict[str, Any] | None = None,
    ) -> None:
        status_value = status.value if isinstance(status, RunStatus) else status
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs "
                "(id, name, operation, status, path, created_at, parent_id, tags, params)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    name,
                    operation,
                    status_value,
                    str(path),
                    created_at,
                    parent_id,
                    json.dumps(list(tags)),
                    json.dumps(params or {}, default=str),
                ),
            )

    def get(self, run_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._row_to_dict(row)

    def list(
        self,
        *,
        status: RunStatus | None = None,
        tags: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> tuple[dict[str, Any], ...]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        for tag in tags:
            clauses.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM runs{where} ORDER BY created_at DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return tuple(self._row_to_dict(row) for row in rows)

    def query(self, where_expr: str) -> tuple[dict[str, Any], ...]:
        stripped = where_expr.strip()
        if stripped.lower().startswith(_ALLOWED_PREFIXES):
            sql = stripped
        else:
            sql = f"SELECT * FROM runs WHERE {stripped}"
        _ensure_select(sql)
        try:
            with self._connect() as conn:
                rows = conn.execute(sql).fetchall()
        except sqlite3.Error as error:
            raise ValueError(f"Invalid query: {error}") from error
        return tuple(self._row_to_dict(row) for row in rows)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for field in ("tags", "params"):
            if field in data:
                data[field] = _decode_json_field(data[field])
        return data
