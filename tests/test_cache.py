from __future__ import annotations

from pathlib import Path

from rlab import cache_path, cache_size, list_cache
from rlab.cache import (
    cache_key,
    list_cache as list_cache_from_module,
    read_jsonl,
    runtime_cache_path,
    write_jsonl_atomic,
    write_through_jsonl_atomic,
)


def test_cache_helpers_are_rust_backed(tmp_path: Path) -> None:
    cache = tmp_path / ".rlab" / "cache"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text("{}", encoding="utf-8")
    (cache / "blob").write_bytes(b"abc")

    entries = list_cache(tmp_path)

    assert cache_path(tmp_path) == cache
    assert [entry.path.name for entry in entries] == ["blob", "registry.json"]
    assert [entry.kind for entry in entries] == ["file", "json"]
    assert cache_size(entries) == 5
    assert list_cache_from_module(tmp_path)[0].size_bytes == 3


def test_runtime_jsonl_cache_helpers(tmp_path: Path) -> None:
    class Context:
        cache_dir = tmp_path / "cache"

    key = cache_key({"b": 2, "a": 1})
    path = runtime_cache_path(Context(), "sources", f"{key}.jsonl")

    assert path == tmp_path / "cache" / "sources" / f"{key}.jsonl"
    assert key == cache_key({"a": 1, "b": 2})

    write_jsonl_atomic(path, [{"text": "one"}, {"text": "two"}])

    assert list(read_jsonl(path)) == [{"text": "one"}, {"text": "two"}]

    passthrough = list(
        write_through_jsonl_atomic(path, ["three"], lambda text: {"text": text})
    )

    assert passthrough == ["three"]
    assert list(read_jsonl(path)) == [{"text": "three"}]
