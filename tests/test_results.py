from __future__ import annotations

import json
from pathlib import Path

from rlab import (
    ArtifactStore,
    FigureArtifact,
    FileArtifact,
    LogArtifact,
    TableArtifact,
)
from rlab.results import FileArtifact as ModuleFileArtifact


def test_result_artifacts_are_rust_backed(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    artifact = FileArtifact(
        "weights",
        path,
        metadata={"sha256": "abc"},
    )

    payload = artifact.to_event_payload()

    assert artifact.path == path
    assert artifact.kind == "file"
    assert artifact.metadata == {"sha256": "abc"}
    assert payload == {
        "schema_version": 1,
        "kind": "file",
        "name": "weights",
        "path": str(path),
        "version": "1",
        "metadata": {"sha256": "abc"},
    }
    assert json.loads(artifact.to_json()) == payload
    assert ModuleFileArtifact("x", path).kind == "file"


def test_specialized_artifacts_are_rust_backed(tmp_path: Path) -> None:
    assert FigureArtifact("plot", tmp_path / "plot.png").kind == "figure"
    assert TableArtifact("rows", tmp_path / "rows.json").kind == "table"
    assert LogArtifact("stdout", tmp_path / "stdout.txt").kind == "log"


def test_artifact_store_resolves_versions_and_aliases(tmp_path: Path) -> None:
    source = tmp_path / "model.bin"
    source.write_bytes(b"weights")
    store = ArtifactStore(tmp_path)

    promoted = store.promote(
        source,
        "model",
        "tiny",
        "2026-06-18",
        alias="candidate",
    )

    by_version = store.describe("artifact:model/tiny@2026-06-18")
    by_alias = store.describe("artifact:model/tiny@candidate")

    assert promoted.object_path == by_version.object_path
    assert by_alias.version == "2026-06-18"
    assert store.resolve_path("artifact:model/tiny@candidate") == promoted.object_path
    assert store.parse_reference("artifact:model/tiny@candidate") == {
        "kind": "model",
        "name": "tiny",
        "version": "candidate",
    }
