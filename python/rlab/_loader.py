"""Import project modules and collect declarative registry records."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Final

from ._project import Project, pinned_project

ERROR_ROOT_MISSING: Final = "project root does not exist: {root}"
ERROR_EMPTY_MODULE: Final = "module names cannot be empty"
ERROR_STRICT_EMPTY_DISCOVERY: Final = "strict discovery produced no registry records"

ROOT_SYS_PATH_INDEX: Final = 0
PACKAGE_PREFIX: Final = "{module}."


def load_modules(
    project_root: str | Path,
    modules: Iterable[str],
    *,
    strict: bool,
) -> Project:
    """Import configured modules under a pinned project and return it."""
    root = _validated_project_root(project_root)
    project = Project(root=root)
    discover_modules(project, root, modules)

    if strict and not project.records:
        raise ValueError(ERROR_STRICT_EMPTY_DISCOVERY)

    return project


def discover_modules(
    project: Project,
    project_root: str | Path,
    modules: Iterable[str],
) -> None:
    """Deterministically import configured packages into an existing project."""
    root = _validated_project_root(project_root)
    _ensure_importable_root(root)

    with pinned_project(project):
        for module_name in _validated_module_names(modules):
            _import_discovered_modules(module_name)


def _validated_project_root(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()
    if root.exists():
        return root

    raise FileNotFoundError(ERROR_ROOT_MISSING.format(root=root))


def _ensure_importable_root(root: Path) -> None:
    root_text = str(root)
    if root_text in sys.path:
        return

    sys.path.insert(ROOT_SYS_PATH_INDEX, root_text)


def _validated_module_names(modules: Iterable[str]) -> tuple[str, ...]:
    return tuple(_validated_module_name(module_name) for module_name in modules)


def _validated_module_name(module_name: str) -> str:
    normalized = str(module_name).strip()
    if normalized:
        return normalized

    raise ValueError(ERROR_EMPTY_MODULE)


def _import_discovered_modules(module_name: str) -> None:
    module = importlib.import_module(module_name)
    for discovered in _expanded_module_names(module, module_name):
        if discovered != module_name:
            importlib.import_module(discovered)


def _expanded_module_names(module: ModuleType, module_name: str) -> Iterator[str]:
    yield module_name

    module_path = _package_path(module)
    if module_path is None:
        return

    yield from _iter_child_module_names(module_path, module_name)


def _package_path(module: ModuleType) -> list[str] | None:
    path = getattr(module, "__path__", None)
    return path if isinstance(path, list) else None


def _iter_child_module_names(module_path: list[str] | None, module_name: str) -> Iterator[str]:
    yield from sorted(
        child.name
        for child in pkgutil.walk_packages(
            module_path,
            prefix=PACKAGE_PREFIX.format(module=module_name),
        )
    )
