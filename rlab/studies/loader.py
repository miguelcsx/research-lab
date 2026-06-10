from __future__ import annotations

from pathlib import Path

from rlab.constants import EntryKind
from rlab.errors import RegistryError
from rlab.registry.resolve import resolve_definition
from rlab.registry.store import Registry
from rlab.studies.model import Study


def load_study(registry: Registry, path: Path) -> tuple[str, Study]:
    resolved = path.resolve()
    import rlab

    project = rlab.Project(f"_study_loader_{id(registry)}", registry=registry)
    from rlab.experiments.loader import _purge_records_from_source, _run_module_with_lab

    _purge_records_from_source(registry, resolved)
    _run_module_with_lab(resolved, project)
    matches = [
        record
        for record in registry.list(EntryKind.STUDY)
        if record.source and record.source.resolve() == resolved
    ]
    if not matches:
        raise RegistryError(f"No @rlab.study found in {path}")
    if len(matches) > 1:
        names = ", ".join(record.name for record in matches)
        raise RegistryError(f"Multiple @rlab.study in {path}: {names}")
    record = matches[0]
    return record.name, resolve_definition(record.value, Study)
