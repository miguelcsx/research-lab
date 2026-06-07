from pathlib import Path

from rlab.config.loader import load_config
from rlab.context.paths import ProjectPaths
from rlab.context.runtime import RuntimeContext
from rlab.project.loader import load_modules
from rlab.registry.context import using_registry
from rlab.registry.store import Registry


def build_runtime(root: Path, overrides: tuple[str, ...] = ()) -> RuntimeContext:
    config = load_config(root, overrides)
    paths = ProjectPaths.from_config(root, config.paths)
    paths.ensure_runtime_dirs()
    registry = Registry()
    with using_registry(registry):
        load_modules(root, config.modules.load)
    return RuntimeContext(config=config, paths=paths, registry=registry)
