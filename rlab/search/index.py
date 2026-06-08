import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_SEARCH_LIMIT = 50
_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_items (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    path TEXT,
    created_at TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_fts
USING fts5(id UNINDEXED, kind UNINDEXED, title, body);
"""


class SearchIndex:
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

    def index(  # noqa: PLR0913
        self,
        item_id: str,
        kind: str,
        title: str,
        body: str,
        path: Path | None = None,
        created_at: str | None = None,
    ) -> None:
        with self._connect() as conn:
            # Remove old FTS entry if updating
            conn.execute("DELETE FROM search_fts WHERE id = ?", (item_id,))
            # Upsert metadata
            conn.execute(
                """INSERT OR REPLACE INTO search_items (id, kind, title, body, path, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, kind, title, body, str(path) if path else None, created_at),
            )
            # Insert into FTS
            conn.execute(
                "INSERT INTO search_fts (id, kind, title, body) VALUES (?, ?, ?, ?)",
                (item_id, kind, title, body),
            )

    def search(
        self,
        text: str,
        *,
        kinds: tuple[str, ...] = (),
        limit: int = _DEFAULT_SEARCH_LIMIT,
    ) -> tuple[dict[str, object], ...]:
        with self._connect() as conn:
            if kinds:
                placeholders = ",".join("?" * len(kinds))
                rows = conn.execute(
                    f"""SELECT s.* FROM search_items s
                        JOIN search_fts fts ON s.id = fts.id
                        WHERE search_fts MATCH ? AND s.kind IN ({placeholders})
                        ORDER BY rank LIMIT ?""",
                    (text, *kinds, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT s.* FROM search_items s
                       JOIN search_fts fts ON s.id = fts.id
                       WHERE search_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (text, limit),
                ).fetchall()
        return tuple(dict(r) for r in rows)

    def delete(self, item_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM search_fts WHERE id = ?", (item_id,))
            conn.execute("DELETE FROM search_items WHERE id = ?", (item_id,))
