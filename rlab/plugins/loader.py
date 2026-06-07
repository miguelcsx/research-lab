from collections.abc import Iterable
from pathlib import Path

from rlab.config.models import PluginConfig
from rlab.plugins.entrypoints import installed_entrypoints, metadata_for
from rlab.plugins.metadata import PluginMetadata
from rlab.plugins.project import load_project_module
from rlab.registry.context import using_registry
from rlab.registry.store import Registry


def load_installed_plugins(registry: Registry) -> tuple[PluginMetadata, ...]:
    metadata: list[PluginMetadata] = []
    for entrypoint in installed_entrypoints():
        item = metadata_for(entrypoint)
        try:
            with using_registry(registry):
                register = entrypoint.load()
                register(registry)
            item = item.model_copy(update={"loaded": True})
        except Exception as error:  # plugin failures are reported, not fatal
            item = item.model_copy(update={"error": str(error)})
        metadata.append(item)
    return tuple(metadata)


def load_project_plugins(root: Path, config: PluginConfig) -> tuple[Path, ...]:
    return tuple(path for module in config.modules for path in load_project_module(root, module))


def load_plugins(
    registry: Registry, root: Path, config: PluginConfig
) -> tuple[PluginMetadata, ...]:
    registry.allow_project_overrides = config.allow_project_overrides
    installed = load_installed_plugins(registry)
    if config.autoload:
        with using_registry(registry):
            load_project_plugins(root, config)
    return installed


def plugin_failures(metadata: Iterable[PluginMetadata]) -> tuple[PluginMetadata, ...]:
    return tuple(item for item in metadata if item.error)
