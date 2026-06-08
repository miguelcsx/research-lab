import os
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rlab.config.models import LabConfig
from rlab.config.overrides import apply_overrides, parse_overrides
from rlab.config.resolver import resolve_values
from rlab.errors import ConfigError


def _environment_overrides() -> dict[str, str]:
    prefix = "RLAB__"
    return {
        key.removeprefix(prefix).lower().replace("__", "."): value
        for key, value in os.environ.items()
        if key.startswith(prefix)
    }


def load_config(root: Path, cli_overrides: Iterable[str] = ()) -> LabConfig:
    path = root / "lab.toml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as stream:
            try:
                data = tomllib.load(stream)
            except tomllib.TOMLDecodeError as error:
                raise ConfigError(f"{path}: {error}") from error
    overrides = {**_environment_overrides(), **parse_overrides(cli_overrides)}
    resolved = resolve_values(apply_overrides(data, overrides), project_root=root)
    if "project" not in resolved:
        resolved["project"] = {"name": root.name}
    try:
        return LabConfig.model_validate(resolved)
    except ValidationError as error:
        raise ConfigError(str(error)) from error
