import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from rlab.errors import ConfigError


def parse_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_overrides(values: Iterable[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in values:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise ConfigError(f"Invalid override {item!r}; expected key=value")
        parsed[key] = parse_value(value)
    return parsed


def apply_overrides(data: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(data))
    for dotted_key, value in overrides.items():
        target = result
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            child = target.setdefault(part, {})
            if not isinstance(child, dict):
                raise ConfigError(f"Cannot override nested key {dotted_key!r}")
            target = child
        target[parts[-1]] = value
    return result
