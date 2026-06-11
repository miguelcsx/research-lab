"""Import project modules and collect declarative registry records."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

from ._project import Project, pinned_project


def load_modules(
    project_root: str | Path, modules: Iterable[str], *, strict: bool
) -> Project:
    """Import configured modules under a pinned project and return it."""
    root = _validated_project_root(project_root)
    _ensure_importable_root(root)

    project = Project(root=root)

    with pinned_project(project):
        for module_name in _validated_module_names(modules):
            _import_discovered_modules(module_name)

    if strict and not project.records:
        raise ValueError("strict discovery produced no registry records")

    return project


def _validated_project_root(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()

    if not root.exists():
        raise FileNotFoundError(f"project root does not exist: {root}")

    return root


def _ensure_importable_root(root: Path) -> None:
    root_text = str(root)

    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def _validated_module_names(modules: Iterable[str]) -> list[str]:
    return [_validated_module_name(module_name) for module_name in modules]


def _validated_module_name(module_name: str) -> str:
    normalized = str(module_name).strip()

    if not normalized:
        raise ValueError("module names cannot be empty")

    return normalized


def _import_discovered_modules(module_name: str) -> None:
    for discovered in _expand_module(module_name):
        importlib.import_module(discovered)


def _expand_module(module_name: str) -> list[str]:
    module = importlib.import_module(module_name)
    names = [module_name]

    if not _is_package(module):
        return names

    names.extend(_iter_child_module_names(module, module_name))
    return names


def _is_package(module: ModuleType) -> bool:
    return getattr(module, "__path__", None) is not None


def _iter_child_module_names(module: ModuleType, module_name: str) -> list[str]:
    module_path = getattr(module, "__path__", None)

    if module_path is None:
        return []

    return [
        child.name
        for child in pkgutil.iter_modules(module_path, prefix=f"{module_name}.")
        if not child.ispkg
    ]
