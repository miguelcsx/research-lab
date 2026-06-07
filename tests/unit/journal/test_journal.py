from __future__ import annotations

from pathlib import Path

from rlab.constants import IdeaStatus
from rlab.journal.decisions import add_decision, list_decisions
from rlab.journal.ideas import add_idea, link_idea, list_ideas, promote_idea
from rlab.journal.negative import add_negative, list_negatives, search_negatives
from rlab.journal.notes import add_note, list_notes


def test_notes_decisions_negative_results_and_ideas(tmp_path: Path) -> None:
    notes_file = tmp_path / "notes.jsonl"
    add_note(notes_file, "note A")
    add_note(notes_file, "note B", author="researcher")
    notes = list_notes(notes_file)
    assert len(notes) == 2
    assert notes[1].author == "researcher"

    decisions_file = tmp_path / "decisions.jsonl"
    decision = add_decision(decisions_file, "Promote clean_v3", selected_run="run_012")
    assert decision.selected_run == "run_012"
    assert list_decisions(decisions_file)[0].rationale.startswith("Promote")

    negatives_file = tmp_path / "negatives.jsonl"
    add_negative(negatives_file, "dedup helps", "tried minhash at 0.8", "no improvement")
    assert list_negatives(negatives_file)[0].hypothesis == "dedup helps"
    assert len(search_negatives(negatives_file, "minhash")) == 1
    assert not search_negatives(negatives_file, "unrelated")

    ideas_file = tmp_path / "ideas.jsonl"
    idea = add_idea(ideas_file, "Try source-balanced corpus")
    assert idea.status == IdeaStatus.IDEA
    linked = link_idea(ideas_file, idea.id, "run:001")
    assert linked is not None
    assert "run:001" in linked.linked_runs
    promoted = promote_idea(ideas_file, idea.id, status=IdeaStatus.PLANNED)
    assert promoted is not None
    assert promoted.status == IdeaStatus.PLANNED
    assert len(list_ideas(ideas_file, status=IdeaStatus.PLANNED)) == 1


def test_idea_missing_id_returns_none(tmp_path: Path) -> None:
    ideas_file = tmp_path / "ideas.jsonl"
    assert link_idea(ideas_file, "missing", "run:001") is None
    assert promote_idea(ideas_file, "missing", status=IdeaStatus.PLANNED) is None
