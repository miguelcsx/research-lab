"""Import project modules and collect declarative registry records."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

from ._project import Project, pinned_project


def load_modules(project_root: str | Path, modules: Iterable[str], *, strict: bool) -> Project:
    """Import configured modules under a pinned project and return it."""
    root = Path(project_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"project root does not exist: {root}")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    project = Project(root=root)
    with pinned_project(project):
        for module_name in modules:
            if not module_name or not str(module_name).strip():
                raise ValueError("module names cannot be empty")
            for discovered in _expand_module(str(module_name)):
                importlib.import_module(discovered)
    if strict and not project.records:
        raise ValueError("strict discovery produced no registry records")
    return project


def _expand_module(module_name: str) -> list[str]:
    module = importlib.import_module(module_name)
    names = [module_name]
    module_path = getattr(module, "__path__", None)
    if module_path is None:
        return names
    for child in pkgutil.iter_modules(module_path, prefix=f"{module_name}."):
        if not child.ispkg:
            names.append(child.name)
    return names
