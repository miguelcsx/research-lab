import importlib
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.constants import EntryKind
from rlab.project.project import _pin_lab_name, _unpin_lab_name
from rlab.registry.context import current_registry
from rlab.registry.store import Registry


class ModuleLoadResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    loaded: bool
    error: str | None = None
    registered_kinds: tuple[str, ...] = ()


def load_modules(root: Path, names: tuple[str, ...]) -> tuple[ModuleLoadResult, ...]:
    """Import each module name under project root; capture errors per-module."""
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    registry = current_registry()
    # Pin a fresh, loader-owned Project for the duration of the import so the
    # template's ``lab = rlab.Project("{name}")`` rebinds to a registry the
    # loader controls. Unpinned, the Project singleton (keyed by name) would
    # hand back a Project from an earlier session whose registry is stale.
    import rlab

    loader_project = rlab.Project(f"_loader_{id(registry)}", registry=registry)
    pin = _pin_lab_name(loader_project)

    results: list[ModuleLoadResult] = []
    try:
        for name in names:
            before = {(r.kind, r.name) for r in registry.list()}
            try:
                if name in sys.modules:
                    # The module is already loaded. Drop it (and any parents)
                    # from ``sys.modules`` so the next import runs from disk.
                    # We also clear any registry records whose ``source`` is
                    # the file we are about to re-import, so the module-level
                    # decorators can re-register cleanly instead of raising
                    # on duplicate entries.
                    resolved = _resolve_module_path(name, root)
                    if resolved is not None:
                        _purge_records_from_source(registry, resolved)
                    _purge_from_sys_modules(name)
                importlib.import_module(name)
                # After import, the loader's registry already received any
                # records because the templates' `lab = rlab.Project(...)` is
                # pinned to the loader's project.
                after = {(r.kind, r.name) for r in registry.list()}
                new_kinds = tuple(
                    sorted(
                        {EntryKind(k) for k, _ in (after - before)},
                        key=lambda e: e.value,
                    )
                )
                results.append(
                    ModuleLoadResult(name=name, loaded=True, registered_kinds=new_kinds)
                )
            except Exception as exc:  # noqa: BLE001 — module failures reported
                results.append(ModuleLoadResult(name=name, loaded=False, error=str(exc)))
    finally:
        _unpin_lab_name(pin)
    return tuple(results)


def _purge_from_sys_modules(name: str) -> None:
    """Remove `name` and any parents in sys.modules so re-import is clean."""
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        key = ".".join(parts[:i])
        sys.modules.pop(key, None)


def _resolve_module_path(name: str, root: Path) -> Path | None:
    """Return the on-disk path for `name` under `root`, or None if not found."""
    parts = name.split(".")
    candidate = root.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate.resolve()
    candidate = root.joinpath(*parts, "__init__.py")
    if candidate.exists():
        return candidate.resolve()
    return None


def _purge_records_from_source(registry: Registry, source: Path) -> None:
    """Remove every record whose ``source`` matches the file being reloaded."""
    resolved = source.resolve()
    for record in list(registry.list()):
        if record.source is not None and Path(record.source).resolve() == resolved:
            registry.remove(record.kind, record.name)

