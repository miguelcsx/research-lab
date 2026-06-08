from __future__ import annotations

from pathlib import Path

import pytest

from rlab.artifacts.audit import AuditTrail
from rlab.artifacts.layout import alias_path, metadata_path, object_path
from rlab.artifacts.lineage import ArtifactLineageGraph
from rlab.artifacts.store import ArtifactStore


def test_layout_helpers(tmp_path: Path) -> None:
    assert object_path(tmp_path, "abcdef") == tmp_path / "objects" / "ab" / "cdef"
    assert metadata_path(tmp_path, "model", "tiny").suffix == ".yaml"
    assert alias_path(tmp_path, "model", "tiny", "candidate").name == "candidate"


def test_audit_trail_record_and_replay(tmp_path: Path) -> None:
    trail = AuditTrail(tmp_path / "audit.jsonl")
    assert trail.replay() == ()
    event = trail.record("invalidate", "x", actor="me", reason="r", metadata={"k": "v"})
    assert event.action == "invalidate"
    replay = trail.replay()
    assert len(replay) == 1
    assert replay[0].metadata == {"k": "v"}


def test_lineage_neighbors_ancestors_query(tmp_path: Path) -> None:
    graph = ArtifactLineageGraph(tmp_path / "lineage.db")
    graph.add_node("orphan", kind="thing", label="L", metadata={"x": 1})
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    assert "b" in graph.neighbors("a")
    assert "c" in graph.descendants("a")
    assert "a" in graph.ancestors("c")
    rows = graph.query("SELECT id FROM lineage_nodes WHERE id = 'orphan'")
    assert rows and rows[0]["id"] == "orphan"
    with pytest.raises(ValueError):
        graph.query("DELETE FROM lineage_nodes")


def test_artifact_store_put_get_alias_delete_and_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    source = tmp_path / "data.txt"
    source.write_text("hello", encoding="utf-8")
    manifest = store.put("model", "tiny", "1", source, alias="candidate")
    assert manifest.sha256
    assert store.get("model", "tiny", "candidate").exists()
    assert store.get("model", "tiny", "1").exists()
    listed = store.index.list()
    assert any(row["name"] == "tiny" for row in listed)
    resolved = store.index.resolve("model", "tiny", "candidate")
    assert resolved is not None and resolved["version"] == "1"
    store.index.deprecate("model", "tiny", "1")
    deprecated = store.index.resolve("model", "tiny", "1")
    assert deprecated is not None and deprecated["deprecated"] == 1

    directory = tmp_path / "bundle"
    directory.mkdir()
    (directory / "a.txt").write_text("a", encoding="utf-8")
    (directory / "b.txt").write_text("b", encoding="utf-8")
    store.put("dataset", "bundle", "1", directory, alias="approved")
    stored = store.get("dataset", "bundle", "approved")
    assert stored.is_dir()

    store.delete("model", "tiny", "1")
    assert store.index.resolve("model", "tiny", "1") is None

    # missing artifact returns a synthetic path
    assert store.get("nope", "nope", "nope").name == "nope"
