import importlib.util
import sys
from pathlib import Path
from typing import cast

from rlab.constants import EntryKind
from rlab.experiments.model import Experiment
from rlab.registry.context import using_registry
from rlab.registry.store import Registry


def load_file(path: Path) -> None:
    """Import a Python file by path, executing its top-level decorators."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)


def load_experiment(registry: Registry, path: Path) -> tuple[str, Experiment]:
    resolved = path.resolve()
    with using_registry(registry):
        load_file(resolved)
    matches = [
        record
        for record in registry.list(EntryKind.EXPERIMENT)
        if record.source and record.source.resolve() == resolved
    ]
    if len(matches) != 1:
        raise ValueError(f"{path} must register exactly one experiment")
    record = matches[0]
    return record.name, cast(Experiment, record.value())
