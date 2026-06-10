"""Typing-only helpers for rlab."""

from __future__ import annotations

from typing import Protocol


class SupportsMetricLogging(Protocol):
    def log_metric(self, name: str, value: float) -> None: ...
