from __future__ import annotations

from pathlib import Path

from rlab.assumptions import Assumption, Threat, render_validity_report
from rlab.baseline.model import BaselineEntry
from rlab.baseline.store import BaselineStore
from rlab.constants import RunStatus
from rlab.data.genealogy import DataGenealogyGraph
from rlab.data.mixing import DataMixReport
from rlab.reports.export import (
    export_repro_zip,
    freeze_run,
    generate_citation_cff,
    generate_methods_section,
    is_locked,
    lock_run,
)
from rlab.reports.latex import render_latex_table
from rlab.reports.markdown import render_run_report
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
from rlab.runs.writer import RunWriter


def test_markdown_latex_freeze_lock_and_exports(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run_001")
    writer = RunWriter(layout)
    writer.metric("accuracy", 0.92)
    writer.params({"lr": 0.001})
    writer.note("Great results!")
    (layout.root / "run.yaml").write_text("name: run_001\n", encoding="utf-8")

    report = render_run_report(layout.root)
    assert "accuracy" in report
    assert "Notes" in report
    assert "empty" in render_run_report(RunLayout(root=tmp_path / "empty").root)

    latex = render_latex_table(
        [{"model": "gpt2", "accuracy": "0.85"}], caption="Main results", label="tab:main"
    )
    assert "\\begin{table}" in latex
    assert render_latex_table([]) == ""

    frozen = freeze_run(layout.root, "paper-run", tmp_path / "frozen")
    assert (frozen / "run.yaml").exists()
    assert export_repro_zip(layout.root).suffix == ".zip"
    assert not is_locked(layout.root)
    lock_run(layout.root)
    assert is_locked(layout.root)
    assert "Miguel Cárdenas" in generate_citation_cff("rlab", "0.1.0", ["Miguel Cárdenas"])
    assert (
        "run_001" in generate_methods_section(layout.root)
        or "experiment" in generate_methods_section(layout.root).lower()
    )


def test_run_lifecycle_transitions(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run_001")
    layout.create()
    assert current_status(layout.root) == RunStatus.CREATED
    start_run(layout.root)
    assert current_status(layout.root) == RunStatus.RUNNING
    finish_run(layout.root)
    assert current_status(layout.root) == RunStatus.COMPLETED
    mark_stale(layout.root)
    assert current_status(layout.root) == RunStatus.STALE
    resume_run(layout.root)
    assert current_status(layout.root) == RunStatus.RUNNING
    cancel_run(layout.root)
    assert current_status(layout.root) == RunStatus.CANCELLED
    fail_run(layout.root, "OutOfMemoryError")
    assert current_status(layout.root) == RunStatus.FAILED
    assert (layout.logs / "error.txt").exists()


def test_baselines_validity_data_genealogy_and_mixing(tmp_path: Path) -> None:
    store = BaselineStore(tmp_path / "baselines.db")
    store.add(
        BaselineEntry(name="gpt2_babylm", metric="eval.accuracy", value=0.82, for_project="babylm")
    )
    assert store.get("gpt2_babylm") is not None
    assert store.get("missing") is None
    assert len(store.list(for_project="babylm")) == 1

    validity = render_validity_report(
        (Assumption(text="Data is i.i.d."),),
        (Threat(text="Single seed.", mitigations=("Replicate with 3 seeds",)),),
    )
    assert "Assumptions" in validity
    assert "Threats to Validity" in validity
    assert "Validity Report" in render_validity_report((), ())

    genealogy = DataGenealogyGraph(tmp_path / "genealogy.db")
    genealogy.add_edge("clean_v2", "raw_v1")
    genealogy.add_edge("clean_v3", "clean_v2")
    assert "raw_v1" in genealogy.ancestors("clean_v3")
    assert "clean_v2" in genealogy.children("raw_v1")
    assert "raw_v1" in genealogy.render_tree("raw_v1")

    mix = DataMixReport(
        sources=("web", "books", "code"), proportions={"web": 0.5, "books": 0.3, "code": 0.2}
    )
    assert mix.dominant_source() == "web"
    assert 0 < mix.balance_score() <= 1.0
    assert DataMixReport(sources=("web",), proportions={"web": 1.0}).balance_score() == 0.0
