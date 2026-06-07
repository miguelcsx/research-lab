from importlib.metadata import EntryPoint, PackageNotFoundError, entry_points, version

from rlab.plugins.metadata import PluginMetadata


def installed_entrypoints() -> tuple[EntryPoint, ...]:
    return tuple(sorted(entry_points(group="rlab.plugins"), key=lambda item: item.name))


def metadata_for(entrypoint: EntryPoint) -> PluginMetadata:
    package = (
        entrypoint.dist.name if entrypoint.dist else entrypoint.module.split(".", maxsplit=1)[0]
    )
    try:
        package_version = version(package)
    except PackageNotFoundError:
        package_version = "0.0.0"
    return PluginMetadata(
        name=entrypoint.name,
        version=package_version,
        package=package,
        entrypoint=entrypoint.value,
    )
