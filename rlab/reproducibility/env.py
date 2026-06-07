import importlib.metadata

from rlab.context.environment import environment_snapshot


def package_snapshot() -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{distribution.metadata['Name']}=={distribution.version}"
            for distribution in importlib.metadata.distributions()
        )
    )


def full_environment() -> dict[str, object]:
    return {**environment_snapshot(), "packages": package_snapshot()}
