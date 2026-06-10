"""Journal convenience models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DecisionEntry:
    text: str
    selected_run: str | None = None
    criteria: Mapping[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class NegativeResultEntry:
    hypothesis: str
    tried: str
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class IdeaEntry:
    text: str
    status: str = "idea"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = ["DecisionEntry", "IdeaEntry", "NegativeResultEntry"]
