from __future__ import annotations

from pathlib import Path

import pytest

from rlab.constants import RunStatus
from rlab.runs.index import RunIndex
from rlab.runs.layout import RunLayout
from rlab.runs.lifecycle import (
    cancel_run,
    current_status,
    fail_run,
    finish_run,
    mark_stale,
    resume_run,
    start_run,
)
from rlab.runs.reader import RunReader
from rlab.runs.writer import RunWriter


def test_layout_paths_and_create(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    layout.create()
    assert layout.logs.exists()
    assert layout.tables.exists()
    assert layout.figures.exists()
    assert layout.artifacts.exists()
    assert layout.results.exists()
    assert layout.metrics_file.name == "metrics.jsonl"
    assert layout.params_file.name == "params.json"
    assert layout.notes_file.name == "notes.jsonl"
    assert layout.status_file.name == "status.txt"
    assert layout.results_file.name == "results.json"
    assert layout.manifest_file.name == "run.yaml"


def test_writer_and_reader_round_trip_and_formats(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    writer = RunWriter(layout)
    writer.metric("loss", 0.3)
    writer.metric("loss", 0.2)
    writer.params({"lr": 0.01})
    writer.params({"bs": 8})
    writer.note("n1", author="me")
    writer.table("scores", [{"a": 1, "b": 2}], fmt="csv")
    writer.table("empty", [], fmt="csv")
    writer.table("json", [{"a": 1}], fmt="json")
    with pytest.raises(ValueError):
        writer.table("bad", [{"a": 1}], fmt="xml")
    writer.results({"final": 0.2})
    writer.error("boom")

    reader = RunReader(layout.root)
    assert reader.metrics_summary()["loss"] == pytest.approx(0.2)
    assert reader.params() == {"lr": 0.01, "bs": 8}
    notes = reader.notes()
    assert notes[0]["text"] == "n1"
    assert reader.results()["final"] == pytest.approx(0.2)
    assert reader.tables()
    assert reader.figures() == ()


def test_reader_missing_files(tmp_path: Path) -> None:
    reader = RunReader(tmp_path / "absent")
    assert reader.status() == RunStatus.CREATED
    assert reader.params() == {}
    assert reader.metrics() == []
    assert reader.metrics_summary() == {}
    assert reader.notes() == []
    assert reader.results() == {}
    assert reader.tables() == ()
    assert reader.figures() == ()
    with pytest.raises(FileNotFoundError):
        reader.manifest()


def test_reader_metrics_summary_falls_back_to_metrics(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    layout.create()
    layout.metrics_file.write_text(
        '{"name": "a", "value": 1.5}\n{"name": "a", "value": 2.5}\n', encoding="utf-8"
    )
    # delete the summary file so reader reconstructs it
    assert RunReader(layout.root).metrics_summary()["a"] == pytest.approx(2.5)


def test_reader_corrupt_files_degrade_gracefully(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    layout.create()
    layout.params_file.write_text("not json", encoding="utf-8")
    layout.metrics_summary_file.write_text("not json", encoding="utf-8")
    layout.results_file.write_text("not json", encoding="utf-8")
    reader = RunReader(layout.root)
    assert reader.params() == {}
    assert reader.metrics_summary() == {}
    assert reader.results() == {}


def test_lifecycle_transitions_and_manifest_patch(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    layout.create()
    layout.manifest_file.write_text("name: r\nstatus: created\n", encoding="utf-8")
    assert current_status(layout.root) == RunStatus.CREATED
    start_run(layout.root)
    assert current_status(layout.root) == RunStatus.RUNNING
    finish_run(layout.root)
    mark_stale(layout.root)
    resume_run(layout.root)
    cancel_run(layout.root)
    fail_run(layout.root, "err")
    assert current_status(layout.root) == RunStatus.FAILED
    assert (layout.logs / "error.txt").read_text(encoding="utf-8") == "err"


def test_lifecycle_handles_missing_or_corrupt_manifest(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "r")
    layout.create()
    # no manifest file: should not raise
    start_run(layout.root)
    layout.manifest_file.write_text("not: [valid yaml", encoding="utf-8")
    finish_run(layout.root)
    # non-dict manifest: should not raise
    layout.manifest_file.write_text("- a\n- b\n", encoding="utf-8")
    cancel_run(layout.root)


def test_run_index_upsert_list_get_query(tmp_path: Path) -> None:
    index = RunIndex(tmp_path / "runs.db")
    index.upsert(
        run_id="r1",
        name="r1",
        operation="experiment",
        status=RunStatus.COMPLETED,
        path=tmp_path / "r1",
        created_at="2026-01-01T00:00:00Z",
        tags=("alpha",),
        params={"lr": 0.1},
    )
    index.upsert(
        run_id="r2",
        name="r2",
        operation="benchmark",
        status="failed",
        path=tmp_path / "r2",
        created_at="2026-01-02T00:00:00Z",
        tags=("beta",),
    )
    rows = index.list(status=RunStatus.COMPLETED)
    assert len(rows) == 1 and rows[0]["id"] == "r1"
    assert index.list(tags=("beta",))[0]["id"] == "r2"
    assert index.list(limit=1)
    assert index.get("r1")["operation"] == "experiment"
    with pytest.raises(KeyError):
        index.get("missing")

    assert index.query("status = 'completed'")[0]["id"] == "r1"
    assert index.query("SELECT id FROM runs WHERE id = 'r2'")[0]["id"] == "r2"
    with pytest.raises(ValueError):
        index.query("DROP TABLE runs")
    with pytest.raises(ValueError):
        index.query("not a valid clause !!")
