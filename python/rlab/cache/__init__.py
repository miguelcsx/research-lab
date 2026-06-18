"""Native cache inspection and JSONL cache helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import TypeVar

from rlab._rlab import (
    CacheEntry,
    cache_key,
    cache_path,
    cache_size,
    list_cache,
    read_jsonl,
    runtime_cache_path,
    write_jsonl_atomic,
    write_through_jsonl_atomic as _write_through_jsonl_atomic,
)

T = TypeVar("T")


def write_through_jsonl_atomic(
    path: Path,
    rows: Iterable[T],
    encode: Callable[[T], Mapping[str, object]],
) -> Iterator[T]:
    yield from _write_through_jsonl_atomic(path, list(rows), encode)


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
