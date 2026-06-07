import importlib
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.constants import EntryKind
from rlab.registry.context import current_registry


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

    results: list[ModuleLoadResult] = []
    for name in names:
        registry = current_registry()
        before = {(r.kind, r.name) for r in registry.list()}
        try:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
            else:
                importlib.import_module(name)
            after = {(r.kind, r.name) for r in registry.list()}
            new_kinds = tuple(
                sorted({EntryKind(k) for k, _ in (after - before)}, key=lambda e: e.value)
            )
            results.append(ModuleLoadResult(name=name, loaded=True, registered_kinds=new_kinds))
        except Exception as exc:  # noqa: BLE001 — module failures are reported, not fatal
            results.append(ModuleLoadResult(name=name, loaded=False, error=str(exc)))
    return tuple(results)
