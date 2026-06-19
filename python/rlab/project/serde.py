"""Project JSON serialization and metadata helpers."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

from rlab._typing import JsonObject, JsonValue

from .constants import (
    ERROR_OBJECT_SEQUENCE,
    ERROR_STRING_LIST,
    ERROR_VALUE_JSON_SERIALIZABLE,
    KEY_REF,
    SIMPLE_JSON_TYPES,
)


def jsonable_spec(value: object) -> JsonValue:
    if isinstance(value, SIMPLE_JSON_TYPES):
        return value

    converted = converted_jsonable(value)
    if converted is not None:
        return converted

    if is_dataclass(value) and not isinstance(value, type):
        config = {
            field.name: jsonable_spec(getattr(value, field.name))
            for field in fields(value)
        }
        rlab_ref = getattr(type(value), "__rlab_ref__", None)
        return (
            {KEY_REF: rlab_ref, **config}
            if isinstance(rlab_ref, str) and rlab_ref
            else config
        )

    if isinstance(value, dict):
        return {str(key): jsonable_spec(child) for key, child in value.items()}

    if isinstance(value, list | tuple):
        return [jsonable_spec(child) for child in value]

    if hasattr(value, "__dict__") and not callable(value):
        return {str(key): jsonable_spec(child) for key, child in vars(value).items()}

    raise TypeError(
        ERROR_VALUE_JSON_SERIALIZABLE.format(type_name=type(value).__name__)
    )


def converted_jsonable(value: object) -> JsonValue | None:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return jsonable_spec(cast(Callable[[], object], to_dict)())

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return jsonable_spec(cast(Callable[[], object], model_dump)())

    return None


def jsonable_mapping(metadata: Mapping[str, object], label: str) -> JsonObject:
    return {key: jsonable_spec(child) for key, child in metadata.items()}


def string_list(value: JsonValue, label: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(ERROR_STRING_LIST.format(label=label))
    if not all(isinstance(item, str) for item in value):
        raise TypeError(ERROR_STRING_LIST.format(label=label))
    return cast(list[str], value)


def object_sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list | tuple):
        raise TypeError(ERROR_OBJECT_SEQUENCE.format(label=label))
    return list(value)


def first_doc_line(obj: object) -> str:
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    return doc.strip().splitlines()[0]


def relative_source(source: str, root: Path) -> str:
    if not source:
        return ""

    path = Path(source)
    resolved_root = root.resolve()
    resolved_path = path.resolve()

    if resolved_path == resolved_root:
        return "."

    if resolved_root in resolved_path.parents:
        return str(resolved_path.relative_to(resolved_root))

    return str(path)
