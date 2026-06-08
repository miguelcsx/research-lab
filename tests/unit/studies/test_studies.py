from __future__ import annotations

from pathlib import Path

from rlab.studies.model import Study
from rlab.studies.store import StudyStore


def test_study_planned_runs() -> None:
    study = Study(
        question="Which tokenizer?",
        variables={"tokenizer": ("a", "b"), "size": ("small", "medium")},
    )
    assert study.planned_runs == 4


def test_study_planned_runs_empty() -> None:
    study = Study(question="Empty")
    assert study.planned_runs == 0


def test_study_store_lifecycle(tmp_path: Path) -> None:
    store = StudyStore(tmp_path / "studies.db")
    store.upsert("tok-study", "Which tokenizer?", domain="nlp", decision_rule="pick best")
    store.link_run("tok-study", "run-1", notes="first")

    studies = store.list()
    assert len(studies) == 1
    assert studies[0]["name"] == "tok-study"

    runs = store.runs_for("tok-study")
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-1"

    exported = store.export()
    assert "tok-study" in exported
