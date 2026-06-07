from pathlib import Path
from typing import cast

from rlab.constants import EntryKind
from rlab.experiments.model import Experiment
from rlab.plugins.project import load_file
from rlab.registry.context import using_registry
from rlab.registry.store import Registry


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
