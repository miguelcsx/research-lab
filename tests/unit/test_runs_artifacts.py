from datetime import UTC, datetime
from pathlib import Path

import pytest

from rlab.artifacts.local import LocalArtifactStore
from rlab.artifacts.metadata import ArtifactIndex
from rlab.constants import RunStatus
from rlab.errors import ManifestError
from rlab.manifests.checksum import sha256, verify_sha256
from rlab.manifests.run import RunManifest
from rlab.runs.ids import run_id
from rlab.runs.index import RunIndex
from rlab.runs.layout import RunLayout
from rlab.runs.lifecycle import transition
from rlab.runs.reader import RunReader
from rlab.runs.writer import RunWriter, atomic_text
from rlab.testing.assertions import assert_metric_exists, assert_valid_run_dir


def manifest(name: str = "run") -> RunManifest:
    now = datetime.now(UTC)
    return RunManifest(
        kind="run",
        name=name,
        version="1",
        operation="test",
        status=RunStatus.CREATED,
        created_at=now,
        updated_at=now,
    )


def test_run_layout_writer_reader_and_index(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run")
    writer = RunWriter(layout)
    running = transition(manifest(), RunStatus.RUNNING)
    writer.yaml(layout.manifest, running)
    writer.metric("accuracy", 0.5, step=1)
    writer.json(layout.results, {"ok": True})
    layout.report.write_text("# report\n")
    layout.command.write_text("rlab run\n")
    layout.git.write_text("{}\n")
    layout.environment.write_text("{}\n")
    reader = RunReader(layout.root)
    assert reader.manifest().status is RunStatus.RUNNING
    assert reader.results() == {"ok": True}
    assert reader.metrics()[0]["name"] == "accuracy"
    assert_valid_run_dir(layout.root)
    assert_metric_exists(layout.root, "accuracy")
    index = RunIndex(tmp_path / "index.sqlite3")
    index.upsert(running, layout.root)
    assert index.list(1)[0]["id"] == "run"
    assert run_id("Hello world", datetime(2026, 1, 1, tzinfo=UTC)).startswith(
        "20260101_000000_hello_world"
    )


def test_lifecycle_and_assertion_failures(tmp_path: Path) -> None:
    running = transition(manifest(), RunStatus.RUNNING)
    assert transition(running, RunStatus.COMPLETED).status is RunStatus.COMPLETED
    with pytest.raises(ValueError):
        transition(running, RunStatus.CREATED)
    with pytest.raises(AssertionError):
        assert_valid_run_dir(tmp_path)
    (tmp_path / "metrics.jsonl").write_text('{"name":"x","value":1}\n')
    with pytest.raises(AssertionError):
        assert_metric_exists(tmp_path, "missing")
    atomic_text(tmp_path / "atomic.txt", "value")
    assert (tmp_path / "atomic.txt").read_text() == "value"


def test_artifact_store(tmp_path: Path) -> None:
    source = tmp_path / "artifact.txt"
    source.write_text("content")
    index = ArtifactIndex(tmp_path / "index.sqlite3")
    store = LocalArtifactStore(tmp_path / "store", index)
    result = store.put(source, artifact_kind="model", name="tiny", version="1")
    assert result.sha256 == sha256(source)
    assert verify_sha256(source, result.sha256)
    assert not verify_sha256(source, "0")
    store.promote("model", "tiny", "1", "best")
    assert store.get("model", "tiny", "best").read_text() == "content"
    assert store.get("model", "tiny").read_text() == "content"
    assert index.list()[0]["name"] == "tiny"
    index.deprecate("model", "tiny", "1")
    store.put(source, artifact_kind="model", name="tiny-copy", version="1")
    stored = store.get("model", "tiny")
    store.delete("model", "tiny", "1")
    assert stored.exists()
    store.delete("model", "tiny-copy", "1")
    assert not stored.exists()
    with pytest.raises(ManifestError):
        store.delete("model", "missing", "1")
    with pytest.raises(ManifestError):
        store.put(tmp_path, artifact_kind="model", name="bad", version="1")
    with pytest.raises(ManifestError):
        store.get("model", "missing")
    with pytest.raises(ManifestError):
        store.promote("model", "missing", "1", "best")
