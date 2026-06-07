from pathlib import Path

from rlab.config.loader import load_config
from rlab.context.paths import ProjectPaths
from rlab.context.runtime import RuntimeContext
from rlab.plugins.loader import load_plugins
from rlab.registry.store import Registry


def build_runtime(root: Path, overrides: tuple[str, ...] = ()) -> RuntimeContext:
    config = load_config(root, overrides)
    paths = ProjectPaths.from_config(root, config.paths)
    paths.ensure_runtime_dirs()
    registry = Registry()
    load_plugins(registry, root, config.plugins)
    return RuntimeContext(config=config, paths=paths, registry=registry)
