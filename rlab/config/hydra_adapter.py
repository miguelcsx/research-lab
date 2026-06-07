import importlib
from collections.abc import Mapping
from typing import Any

from rlab.errors import ConfigError


def compose_hydra(overrides: tuple[str, ...]) -> Mapping[str, Any]:
    try:
        hydra = importlib.import_module("hydra")
    except ImportError as error:
        raise ConfigError("Hydra support requires the 'hydra' optional dependency") from error
    with hydra.initialize(version_base=None, config_path=None):
        return dict(hydra.compose(config_name=None, overrides=list(overrides)))
