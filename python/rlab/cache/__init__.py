"""Cache helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import TypeVar

from rlab._typing import JsonObject, coerce_json_object
from rlab._rlab import CacheEntry, cache_path, cache_size, list_cache

T = TypeVar("T")


def cache_key(value: object) -> str:
    """Stable SHA-256 key for JSON-compatible cache inputs."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def runtime_cache_path(ctx: object, *parts: str) -> Path | None:
    """Path under a runtime context cache, or None outside an rlab run."""
    cache_dir = getattr(ctx, "cache_dir", None)
    if cache_dir is None:
        return None
    return Path(cache_dir).joinpath(*parts)


def read_jsonl(path: Path) -> Iterator[JsonObject]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, Mapping):
                    raise ValueError(f"expected JSON object in {path}")
                yield coerce_json_object(value)


def write_jsonl_atomic(path: Path, rows: Iterable[JsonObject]) -> None:
    for _ in write_through_jsonl_atomic(path, rows, lambda row: row):
        pass


def write_through_jsonl_atomic(
    path: Path, rows: Iterable[T], encode: Callable[[T], JsonObject]
) -> Iterator[T]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(encode(row), sort_keys=True) + "\n")
                yield row
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


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
