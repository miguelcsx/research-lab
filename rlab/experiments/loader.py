import importlib.util
import sys
from pathlib import Path

from rlab.constants import EntryKind
from rlab.experiments.model import Experiment
from rlab.project.project import Project
from rlab.registry.resolve import resolve_definition
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
    # Provide a Project whose registry is the caller's, so that the
    # ``lab = rlab.Project("...")`` line in the file and the
    # ``@lab.experiment(...)`` decorator it drives register into the
    # same registry the experiment loader will inspect. Use a unique
    # name so the Project singleton (keyed by name) does not hand back
    # a stale Project from a previous call whose registry differs.
    import rlab

    project = rlab.Project(f"_experiment_loader_{id(registry)}", registry=registry)
    # Clear any prior records from this file so re-running is idempotent.
    _purge_records_from_source(registry, resolved)
    _run_module_with_lab(resolved, project)
    matches = [
        record
        for record in registry.list(EntryKind.EXPERIMENT)
        if record.source and record.source.resolve() == resolved
    ]
    if len(matches) != 1:
        raise ValueError(f"{path} must register exactly one experiment")
    record = matches[0]
    return record.name, resolve_definition(record.value, Experiment)


def _run_module_with_lab(path: Path, project: Project) -> None:
    """Execute `path`'s module with `project` pre-injected as `lab`.

    The project's name is "pinned" to ``_pin_lab_name`` so the file's
    ``lab = rlab.Project("name")`` line resolves back to ``project`` (since
    ``rlab.Project`` is a singleton-by-name).
    """
    from rlab.project.project import _pin_lab_name, _unpin_lab_name

    pin = _pin_lab_name(project)
    try:
        # Drop any prior cached module with the same stem so re-runs are
        # clean (the previous module would be the same ``path.stem`` even
        # if the disk path changed between tests, since pytest reuses
        # ``tmp_path`` keys).
        sys.modules.pop(path.stem, None)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        module.lab = project  # type: ignore[attr-defined]
        sys.modules[path.stem] = module
        spec.loader.exec_module(module)
    finally:
        _unpin_lab_name(pin)


def _purge_records_from_source(registry: Registry, source: Path) -> None:
    """Remove every record whose ``source`` matches the file being reloaded."""
    resolved = source.resolve()
    for record in list(registry.list()):
        if record.source is not None and Path(record.source).resolve() == resolved:
            registry.remove(record.kind, record.name)
