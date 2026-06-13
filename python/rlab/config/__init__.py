"""Functional access to Rust-owned project and experiment configuration."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from rlab._rlab import (
    diff_config_documents,
    list_config_documents,
    resolve_config_document,
    validate_config_documents,
)
from rlab._typing import JsonObject, JsonValue

DEFAULT_SUFFIX: Final = ".yaml"
DEFAULT_REQUIRE_EXPLICIT_PATHS: Final = True
EMPTY_JSON_OBJECT: Final[JsonObject] = {}

ERROR_CONFIG_OBJECT: Final = "configuration must be a JSON object"

JSON_SORT_KEYS: Final = True

__all__ = ["diff_configs", "list_configs", "resolve_config", "validate_configs"]


def resolve_config(
    root: str | Path,
    name: str,
    *,
    overrides: Mapping[str, JsonValue] | None = None,
    suffix: str = DEFAULT_SUFFIX,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject:
    return _decode_object(
        resolve_config_document(
            Path(root),
            name,
            _encode_object(overrides),
            suffix,
            require_explicit_paths,
        )
    )


def list_configs(root: str | Path, *, suffix: str = DEFAULT_SUFFIX) -> tuple[str, ...]:
    return tuple(list_config_documents(Path(root), suffix))


def validate_configs(
    root: str | Path, *, suffix: str = DEFAULT_SUFFIX
) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in _decode_object(
            validate_config_documents(Path(root), suffix)
        ).items()
    }


def diff_configs(left: JsonObject, right: JsonObject) -> JsonObject:
    return _decode_object(
        diff_config_documents(
            _encode_object(left),
            _encode_object(right),
        )
    )


def _encode_object(value: Mapping[str, JsonValue] | None) -> str:
    return json.dumps(
        dict(value) if value is not None else EMPTY_JSON_OBJECT,
        sort_keys=JSON_SORT_KEYS,
    )


def _decode_object(value: str) -> JsonObject:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise TypeError(ERROR_CONFIG_OBJECT)
    return {str(key): item for key, item in decoded.items()}
