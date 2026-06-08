import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);
"""


class KnowledgeGraph:
    """SQLite-backed local knowledge graph for research provenance."""

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

    def add_node(
        self,
        node_id: str,
        kind: str,
        label: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO graph_nodes
                   (id, kind, label, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    node_id,
                    kind,
                    label,
                    json.dumps(metadata or {}),
                    datetime.now(tz=UTC).isoformat(),
                ),
            )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str = "produced",
        weight: float = 1.0,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO graph_edges
                   (source_id, target_id, relation, weight, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (source_id, target_id, relation, weight, datetime.now(tz=UTC).isoformat()),
            )

    def neighbors(self, node_id: str, *, relation: str | None = None) -> tuple[str, ...]:
        with self._connect() as conn:
            if relation:
                rows = conn.execute(
                    "SELECT target_id FROM graph_edges WHERE source_id = ? AND relation = ?",
                    (node_id, relation),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT target_id FROM graph_edges WHERE source_id = ?",
                    (node_id,),
                ).fetchall()
        return tuple(r["target_id"] for r in rows)

    def query(self, sql: str, params: tuple[object, ...] = ()) -> tuple[dict[str, object], ...]:
        stripped = sql.lstrip().lower()
        if not (stripped.startswith("select") or stripped.startswith("with")):
            raise ValueError("Only SELECT/WITH queries are permitted")
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(dict(r) for r in rows)

    def lineage(self, node_id: str, depth: int = 5) -> tuple[tuple[str, str], ...]:
        """Return (source, target) pairs reachable from node_id."""
        edges: list[tuple[str, str]] = []
        visited: set[str] = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            if not frontier:
                break
            placeholders = ",".join("?" * len(frontier))
            with self._connect() as conn:
                rows = conn.execute(
                    f"SELECT source_id, target_id FROM graph_edges"
                    f" WHERE source_id IN ({placeholders})",
                    tuple(frontier),
                ).fetchall()
            new_frontier: set[str] = set()
            for row in rows:
                src, tgt = row["source_id"], row["target_id"]
                edges.append((src, tgt))
                if tgt not in visited:
                    visited.add(tgt)
                    new_frontier.add(tgt)
            frontier = new_frontier
        return tuple(edges)