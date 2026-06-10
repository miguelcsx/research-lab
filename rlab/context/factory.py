from pathlib import Path

from rlab.config.loader import load_config
from rlab.context.paths import ProjectPaths
from rlab.context.runtime import RuntimeContext
from rlab.data.sinks import register_builtin_sinks
from rlab.errors import ModuleLoadError
from rlab.project.loader import load_modules
from rlab.registry.context import using_registry
from rlab.registry.store import Registry


def build_runtime(
    root: Path, overrides: tuple[str, ...] = (), *, strict: bool = False
) -> RuntimeContext:
    config = load_config(root, overrides)
    paths = ProjectPaths.from_config(root, config.paths)
    paths.ensure_runtime_dirs()
    registry = Registry()
    with using_registry(registry):
        register_builtin_sinks(registry)
        results = load_modules(root, config.modules.load)
    if strict:
        failures = [r for r in results if not r.loaded]
        if failures:
            names = ", ".join(f.name for f in failures)
            errors = "; ".join(f"{f.name}: {f.error}" for f in failures)
            raise ModuleLoadError(f"Failed to load modules ({names}): {errors}")
    return RuntimeContext(config=config, paths=paths, registry=registry)
