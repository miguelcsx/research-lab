from __future__ import annotations

import json
from pathlib import Path

from rlab import ArtifactRef, RunRef
from rlab._runner import _ChildContext, _child_command, _run_data


def test_child_command_serializes_artifact_refs(tmp_path: Path) -> None:
    artifact = ArtifactRef(
        run_id="run",
        name="tokenizer",
        path=tmp_path / "tokenizer",
        kind="directory",
        metadata={},
    )

    command = _child_command(tmp_path, "workflow:encode", {"tokenizer_path": artifact})

    assert command[-2:] == ["--param", f"tokenizer_path={tmp_path / 'tokenizer'}"]


def test_run_ref_resolves_named_artifacts(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "artifacts.jsonl").write_text(
        json.dumps(
            {
                "name": "encoded.train",
                "kind": "directory",
                "path": str(tmp_path / "outputs" / "encoded" / "train"),
                "staged_path": str(tmp_path / "artifacts" / "directory" / "encoded.train"),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    ref = RunRef("run", "workflow:encode", tmp_path).artifact("encoded.train")

    assert ref.kind == "directory"
    assert ref.path == tmp_path / "artifacts" / "directory" / "encoded.train"


def test_run_ref_reads_metric_summary(tmp_path: Path) -> None:
    (tmp_path / "metrics_summary.json").write_text(
        json.dumps({"validation.loss": 1.25}),
        encoding="utf-8",
    )

    assert RunRef("run", "experiment:x", tmp_path).metric("validation.loss") == 1.25


def test_run_data_accepts_single_run_sweeps(tmp_path: Path) -> None:
    data = _run_data({"data": {"runs": ["experiment_x"]}}, tmp_path)

    assert data["id"] == "experiment_x"
    assert data["path"] == str(tmp_path / ".rlab" / "runs" / "experiment_x")


def test_child_context_saves_lineage_artifact(tmp_path: Path) -> None:
    class Base:
        project_root = tmp_path
        saved: tuple[str, Path, str] | None = None

        def output_path(self, name: str) -> Path:
            return tmp_path / name

        def save_artifact(self, name: str, path: Path, *, kind: str) -> None:
            self.saved = (name, path, kind)

    base = Base()
    ctx = _ChildContext(base)  # type: ignore[arg-type]
    ctx._children.append({"id": "child", "target": "workflow:x", "path": "/runs/child"})

    ctx.save_children()

    assert json.loads((tmp_path / "children.json").read_text()) == [
        {"id": "child", "target": "workflow:x", "path": "/runs/child"}
    ]
    assert base.saved == ("run.children", tmp_path / "children.json", "file")
