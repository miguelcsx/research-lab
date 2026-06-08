import importlib
import importlib.util
from collections.abc import Mapping
from typing import Any

from rlab.errors import ConfigError


def compose_hydra(overrides: tuple[str, ...]) -> Mapping[str, Any]:
    if importlib.util.find_spec("hydra") is None:
        raise ConfigError("Hydra support requires the 'hydra' optional dependency")
    hydra = importlib.import_module("hydra")
    with hydra.initialize(version_base=None, config_path=None):
        return dict(hydra.compose(config_name=None, overrides=list(overrides)))
