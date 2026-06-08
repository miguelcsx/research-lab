import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

_DEFAULT_ANCESTOR_DEPTH = 10
_SCHEMA = """
CREATE TABLE IF NOT EXISTS dataset_ancestry (
    child TEXT NOT NULL,
    parent TEXT NOT NULL,
    transform TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (child, parent)
);
"""


class DataGenealogyGraph:
    """Tracks parent/child relationships between dataset variants."""

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

    def add_edge(self, child: str, parent: str, transform: str | None = None) -> None:

        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO dataset_ancestry VALUES (?, ?, ?, ?)",
                (child, parent, transform, datetime.now(tz=UTC).isoformat()),
            )

    def parents(self, name: str) -> tuple[str, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT parent FROM dataset_ancestry WHERE child = ?", (name,)
            ).fetchall()
        return tuple(r["parent"] for r in rows)

    def children(self, name: str) -> tuple[str, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT child FROM dataset_ancestry WHERE parent = ?", (name,)
            ).fetchall()
        return tuple(r["child"] for r in rows)

    def ancestors(self, name: str, depth: int = _DEFAULT_ANCESTOR_DEPTH) -> tuple[str, ...]:
        visited: set[str] = set()
        frontier = {name}
        for _ in range(depth):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for node in frontier:
                for p in self.parents(node):
                    if p not in visited and p != name:
                        visited.add(p)
                        next_frontier.add(p)
            frontier = next_frontier
        return tuple(sorted(visited))

    def render_tree(self, name: str, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}{name}"]
        for child in self.children(name):
            lines.append(self.render_tree(child, indent + 1))
        return "\n".join(lines)
