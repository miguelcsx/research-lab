from __future__ import annotations

import hashlib
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rlab.artifacts.layout import alias_path, metadata_path, object_path
from rlab.constants import ARTIFACT_INDEX_NAME
from rlab.manifests.artifact import ArtifactManifest

_SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deprecated INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, name, version)
);
CREATE TABLE IF NOT EXISTS aliases (
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    alias TEXT NOT NULL,
    version TEXT NOT NULL,
    PRIMARY KEY (kind, name, alias)
);
"""


def _sha256_of(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    if path.is_dir():
        for file in sorted(path.rglob("*")):
            if file.is_file():
                data = file.read_bytes()
                digest.update(file.relative_to(path).as_posix().encode())
                digest.update(data)
                total += len(data)
    else:
        data = path.read_bytes()
        digest.update(data)
        total = len(data)
    return digest.hexdigest(), total


class ArtifactIndex:
    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def list(self) -> tuple[dict[str, object], ...]:
        with self._store._connect() as conn:
            rows = conn.execute(
                "SELECT kind, name, version, sha256, path, size_bytes, created_at, deprecated"
                " FROM artifacts ORDER BY kind, name, version"
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def resolve(self, kind: str, name: str, version_or_alias: str) -> dict[str, object] | None:
        version = self._store._resolve_alias(kind, name, version_or_alias) or version_or_alias
        with self._store._connect() as conn:
            row = conn.execute(
                "SELECT kind, name, version, sha256, path, size_bytes, created_at, deprecated"
                " FROM artifacts WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            ).fetchone()
        return dict(row) if row else None

    def deprecate(self, kind: str, name: str, version: str) -> None:
        with self._store._connect() as conn:
            conn.execute(
                "UPDATE artifacts SET deprecated = 1 WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            )


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self._db = root / ARTIFACT_INDEX_NAME
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
        self.index = ArtifactIndex(self)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db)
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

    def _resolve_alias(self, kind: str, name: str, alias: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT version FROM aliases WHERE kind = ? AND name = ? AND alias = ?",
                (kind, name, alias),
            ).fetchone()
        return row["version"] if row else None

    def put(
        self,
        kind: str,
        name: str,
        version: str,
        source: Path,
        *,
        alias: str | None = None,
    ) -> ArtifactManifest:
        sha, size = _sha256_of(source)
        dest = object_path(self.root, sha)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
        manifest = ArtifactManifest(
            kind="artifact",
            name=name,
            version=version,
            artifact_kind=kind,
            path=dest,
            sha256=sha,
            size_bytes=size,
            aliases=(alias,) if alias else (),
        )
        meta = metadata_path(self.root, kind, f"{name}@{version}")
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False))
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts "
                "(kind, name, version, sha256, path, size_bytes, created_at, deprecated)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    kind,
                    name,
                    version,
                    sha,
                    str(dest),
                    size,
                    datetime.now(tz=UTC).isoformat(),
                ),
            )
            if alias:
                conn.execute(
                    "INSERT OR REPLACE INTO aliases"
                    " (kind, name, alias, version) VALUES (?, ?, ?, ?)",
                    (kind, name, alias, version),
                )
                link = alias_path(self.root, kind, name, alias)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.write_text(sha + "\n", encoding="utf-8")
        return manifest

    def get(self, kind: str, name: str, version_or_alias: str) -> Path:
        version = self._resolve_alias(kind, name, version_or_alias) or version_or_alias
        with self._connect() as conn:
            row = conn.execute(
                "SELECT path FROM artifacts WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            ).fetchone()
        if row is None:
            return self.root / kind / name / version_or_alias
        return Path(row["path"])

    def delete(self, kind: str, name: str, version: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT sha256 FROM artifacts WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            ).fetchone()
            if row is not None:
                obj = object_path(self.root, row["sha256"])
                if obj.exists():
                    if obj.is_dir():
                        shutil.rmtree(obj)
                    else:
                        obj.unlink()
            conn.execute(
                "DELETE FROM artifacts WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            )
            conn.execute(
                "DELETE FROM aliases WHERE kind = ? AND name = ? AND version = ?",
                (kind, name, version),
            )