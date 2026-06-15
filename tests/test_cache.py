from __future__ import annotations

from pathlib import Path

from rlab import cache_path, cache_size, list_cache
from rlab.cache import list_cache as list_cache_from_module


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
