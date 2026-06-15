"""Rust-backed journal entry models."""

from typing import Literal, TypeAlias

from rlab._rlab import DecisionEntry, IdeaEntry, NegativeResultEntry, NoteEntry

IdeaStatus: TypeAlias = Literal[
    "idea", "planned", "running", "validated", "rejected", "published"
]

__all__ = [
    "DecisionEntry",
    "IdeaEntry",
    "IdeaStatus",
    "NegativeResultEntry",
    "NoteEntry",
]
