"""Small shared helpers for resolved YAML documents."""

from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Mapping
from typing import TypeVar, cast

from rlab._typing import JsonObject, JsonValue

ModelT = TypeVar("ModelT")

EMPTY_JSON_OBJECT: JsonObject = {}


def encode_overrides(value: Mapping[str, JsonValue] | None) -> str:
    return json.dumps(dict(value) if value is not None else EMPTY_JSON_OBJECT, sort_keys=True)


def decode_object(value: str, label: str) -> JsonObject:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise TypeError(f"{label} must be a JSON object")
    return {str(key): item for key, item in decoded.items()}


def apply_overrides(
    document: Mapping[str, JsonValue],
    overrides: Mapping[str, JsonValue] | None,
) -> JsonObject:
    result: JsonObject = deepcopy(dict(document))
    for path, value in (overrides or {}).items():
        target = result
        parts = path.split(".")
        for part in parts[:-1]:
            child = target.setdefault(part, {})
            if not isinstance(child, dict):
                raise ValueError(f"config path crosses non-mapping: {path}")
            target = child
        target[parts[-1]] = value
    return result


def validate_model(model: type[ModelT], value: JsonObject) -> ModelT:
    validate = getattr(model, "model_validate", None)
    if not callable(validate):
        raise TypeError("typed document model must provide model_validate")
    return cast(ModelT, validate(value))


__all__ = ["apply_overrides", "decode_object", "encode_overrides", "validate_model"]
