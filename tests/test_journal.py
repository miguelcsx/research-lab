from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rlab import DecisionEntry, IdeaEntry, NegativeResultEntry, NoteEntry
from rlab.journal import DecisionEntry as ModuleDecisionEntry


def test_journal_entries_are_rust_backed() -> None:
    decision = DecisionEntry(
        "ship the small model",
        selected_run="run-1",
        criteria={"score": "best"},
    )
    negative = NegativeResultEntry("bigger batch helps", "batch=64", "unstable")
    idea = IdeaEntry("try tokenizer dropout", status="planned")
    note = NoteEntry("run-1", "looked good")

    assert decision.text == "ship the small model"
    assert decision.selected_run == "run-1"
    assert decision.criteria == {"score": "best"}
    assert isinstance(decision.created_at, datetime)
    assert decision.created_at.tzinfo == timezone.utc
    assert negative.reason == "unstable"
    assert idea.status == "planned"
    assert idea.id.startswith("idea_")
    assert note.run_id == "run-1"
    assert ModuleDecisionEntry("ok").criteria == {}


def test_idea_status_validates_in_rust() -> None:
    with pytest.raises(ValueError):
        IdeaEntry("bad", status="maybe")  # type: ignore[arg-type]
