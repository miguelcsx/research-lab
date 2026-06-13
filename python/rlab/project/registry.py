"""Project singleton registry and pinning state."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from .facade import Project

_LOCK: Final = threading.RLock()
_PROJECTS: dict[str, "Project"] = {}
_PIN_STACK: list["Project"] = []


def default_project_name() -> str:
    try:
        from rlab._rlab import load_config
    except ImportError:
        return Path.cwd().name

    try:
        return str(load_config(None).project_name)
    except (AttributeError, TypeError, ValueError):
        return Path.cwd().name


def pinned_or_registered_project(cls: type["Project"], name: str | None) -> "Project":
    with _LOCK:
        if _PIN_STACK:
            return _PIN_STACK[-1]

        resolved = name or default_project_name()
        instance = _PROJECTS.get(resolved)
        if instance is not None:
            return instance

        instance = super(cls, cls).__new__(cls)
        _PROJECTS[resolved] = instance
        return instance


@contextmanager
def pinned_project(project: "Project") -> Iterator[None]:
    """Pin a project during dynamic import."""
    with _LOCK:
        _PIN_STACK.append(project)

    try:
        yield
    finally:
        with _LOCK:
            _unpin_project(project)


def _unpin_project(project: "Project") -> None:
    if not _PIN_STACK:
        return

    if _PIN_STACK[-1] is project:
        _PIN_STACK.pop()
        return

    if project in _PIN_STACK:
        _PIN_STACK.remove(project)
