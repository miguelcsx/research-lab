from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lineage_nodes (
    id TEXT PRIMARY KEY,
    kind TEXT,
    label TEXT,
    metadata TEXT
);
CREATE TABLE IF NOT EXISTS lineage_edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL DEFAULT 'derived',
    PRIMARY KEY (source_id, target_id, relation)
);
"""


def _ensure_select(sql: str) -> None:
    stripped = sql.lstrip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        raise ValueError("Only SELECT/WITH queries are permitted")


class ArtifactLineageGraph:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_node(
        self,
        node_id: str,
        kind: str = "",
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lineage_nodes (id, kind, label, metadata) VALUES (?, ?, ?, ?)",
                (node_id, kind, label, json.dumps(metadata or {})),
            )

    def add_edge(self, source_id: str, target_id: str, relation: str = "derived") -> None:
        self.add_node(source_id)
        self.add_node(target_id)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lineage_edges (source_id, target_id, relation) VALUES (?, ?, ?)",
                (source_id, target_id, relation),
            )

    def neighbors(self, node_id: str, *, relation: str | None = None) -> tuple[str, ...]:
        with self._connect() as conn:
            if relation:
                rows = conn.execute(
                    "SELECT target_id FROM lineage_edges WHERE source_id = ? AND relation = ?",
                    (node_id, relation),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT target_id FROM lineage_edges WHERE source_id = ?",
                    (node_id,),
                ).fetchall()
        return tuple(row["target_id"] for row in rows)

    def descendants(self, node_id: str) -> tuple[str, ...]:
        seen: set[str] = set()
        frontier: list[str] = [node_id]
        while frontier:
            current = frontier.pop()
            for child in self.neighbors(current):
                if child not in seen:
                    seen.add(child)
                    frontier.append(child)
        return tuple(sorted(seen))

    def ancestors(self, node_id: str) -> tuple[str, ...]:
        seen: set[str] = set()
        frontier: list[str] = [node_id]
        while frontier:
            current = frontier.pop()
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT source_id FROM lineage_edges WHERE target_id = ?",
                    (current,),
                ).fetchall()
            for row in rows:
                parent = row["source_id"]
                if parent not in seen:
                    seen.add(parent)
                    frontier.append(parent)
        return tuple(sorted(seen))

    def query(self, sql: str, params: tuple[object, ...] = ()) -> tuple[dict[str, object], ...]:
        _ensure_select(sql)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(dict(row) for row in rows)
