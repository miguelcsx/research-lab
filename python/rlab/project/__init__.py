"""Project facade package."""

from __future__ import annotations

from .facade import Project
from .registry import pinned_project

__all__ = ["Project", "pinned_project"]
