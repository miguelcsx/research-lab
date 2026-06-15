from __future__ import annotations

import json
from pathlib import Path

from rlab import FigureArtifact, FileArtifact, LogArtifact, ResultSchema, TableArtifact
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


def test_specialized_artifacts_and_result_schema_are_rust_backed(tmp_path: Path) -> None:
    assert FigureArtifact("plot", tmp_path / "plot.png").kind == "figure"
    assert TableArtifact("rows", tmp_path / "rows.json").kind == "table"
    assert LogArtifact("stdout", tmp_path / "stdout.txt").kind == "log"

    schema = ResultSchema("eval", {"accuracy": "float"})

    assert schema.to_dict() == {
        "name": "eval",
        "fields": {"accuracy": "float"},
        "version": "1",
    }
