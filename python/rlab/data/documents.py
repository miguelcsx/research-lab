"""Functional access to Rust-owned data configuration documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from rlab._rlab import (
    list_data_documents,
    resolve_data_document,
    validate_data_documents,
)
from rlab._typing import JsonObject, JsonValue

DEFAULT_REQUIRE_EXPLICIT_PATHS: Final = True
EMPTY_JSON_OBJECT: Final[JsonObject] = {}
ERROR_DATA_OBJECT: Final = "data document must be a JSON object"
JSON_SORT_KEYS: Final = True

__all__ = ["list_datasets", "resolve_dataset", "validate_datasets"]


def resolve_dataset(
    root: str | Path,
    name: str,
    *,
    overrides: Mapping[str, JsonValue] | None = None,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject:
    return _decode_object(
        resolve_data_document(
            Path(root),
            name,
            _encode_object(overrides),
            require_explicit_paths,
        )
    )


def list_datasets(root: str | Path) -> tuple[str, ...]:
    return tuple(list_data_documents(Path(root)))


def validate_datasets(root: str | Path) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in _decode_object(validate_data_documents(Path(root))).items()
    }


def _encode_object(value: Mapping[str, JsonValue] | None) -> str:
    return json.dumps(
        dict(value) if value is not None else EMPTY_JSON_OBJECT,
        sort_keys=JSON_SORT_KEYS,
    )


def _decode_object(value: str) -> JsonObject:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise TypeError(ERROR_DATA_OBJECT)
    return {str(key): item for key, item in decoded.items()}
