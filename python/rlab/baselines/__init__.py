"""Baseline declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaselineEntry:
    name: str
    metric: str
    value: float
    description: str | None = None


class BaselineStore:
    """In-memory baseline store for tests and small scripts."""

    def __init__(self) -> None:
        self._entries: dict[str, BaselineEntry] = {}

    def add(self, entry: BaselineEntry) -> None:
        self._entries[entry.name] = entry

    def list(self) -> list[BaselineEntry]:
        return list(self._entries.values())


__all__ = ["BaselineEntry", "BaselineStore"]
