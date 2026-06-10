"""Cache inspection helpers for the rlab facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class CacheEntry:
    path: Path
    size_bytes: int
    kind: str


def cache_path(root: str | Path = ".") -> Path:
    return Path(root).joinpath(".rlab", "cache")


def list_cache(root: str | Path = ".") -> list[CacheEntry]:
    base = cache_path(root)
    if not base.exists():
        return list()
    entries: list[CacheEntry] = []
    for path in base.rglob("*"):
        if path.is_file():
            entries.append(CacheEntry(path=path, size_bytes=path.stat().st_size, kind=path.suffix.lstrip(".") or "file"))
    return entries


def cache_size(entries: Iterable[CacheEntry]) -> int:
    return sum(entry.size_bytes for entry in entries)


__all__ = ["CacheEntry", "cache_path", "list_cache", "cache_size"]
