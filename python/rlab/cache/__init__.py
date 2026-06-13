"""Cache inspection helpers for the rlab facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable

CACHE_DIR: Final = ".rlab"
CACHE_NAME: Final = "cache"
ALL_FILES_PATTERN: Final = "*"
DEFAULT_KIND: Final = "file"
SUFFIX_PREFIX: Final = "."


@dataclass(frozen=True, slots=True)
class CacheEntry:
    path: Path
    size_bytes: int
    kind: str


def cache_path(root: str | Path = ".") -> Path:
    return Path(root) / CACHE_DIR / CACHE_NAME


def list_cache(root: str | Path = ".") -> list[CacheEntry]:
    base = cache_path(root)
    if not base.exists():
        return []

    return list(_cache_entries(base))


def cache_size(entries: Iterable[CacheEntry]) -> int:
    return sum(entry.size_bytes for entry in entries)


def _cache_entries(base: Path) -> Iterable[CacheEntry]:
    for path in base.rglob(ALL_FILES_PATTERN):
        if path.is_file():
            yield _cache_entry(path)


def _cache_entry(path: Path) -> CacheEntry:
    return CacheEntry(
        path=path,
        size_bytes=path.stat().st_size,
        kind=_cache_kind(path),
    )


def _cache_kind(path: Path) -> str:
    suffix = path.suffix
    if not suffix:
        return DEFAULT_KIND
    return suffix.lstrip(SUFFIX_PREFIX)


__all__ = ["CacheEntry", "cache_path", "list_cache", "cache_size"]
