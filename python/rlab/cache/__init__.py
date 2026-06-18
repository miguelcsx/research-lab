"""Rust-backed cache inspection and small JSONL cache helpers."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import Protocol, TypeVar

from rlab._rlab import CacheEntry, cache_path, cache_size, list_cache

T = TypeVar("T")


class CacheContext(Protocol):
    @property
    def cache_dir(self) -> Path | None: ...

    @property
    def project_root(self) -> Path: ...


def cache_key(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def runtime_cache_path(ctx: CacheContext, *parts: str) -> Path:
    root = ctx.cache_dir or ctx.project_root / ".rlab" / "cache"
    path = root.joinpath(*parts)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> Iterator[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise TypeError(f"JSONL row must be an object: {path}")
                yield value


def write_jsonl_atomic(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    for _ in write_through_jsonl_atomic(path, rows, lambda row: row):
        pass


def write_through_jsonl_atomic(
    path: Path,
    rows: Iterable[T],
    encode: Callable[[T], Mapping[str, object]],
) -> Iterator[T]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(encode(row)), sort_keys=True) + "\n")
                yield row
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


__all__ = [
    "CacheEntry",
    "cache_key",
    "cache_path",
    "cache_size",
    "list_cache",
    "read_jsonl",
    "runtime_cache_path",
    "write_jsonl_atomic",
    "write_through_jsonl_atomic",
]
