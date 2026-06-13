"""Component signature schema inference and param coercion."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, cast, get_args, get_origin, get_type_hints

from rlab._typing import JsonObject, JsonValue

from .constants import (
    ERROR_COMPONENT_CALLABLE,
    ERROR_COMPONENT_FACTORY_CALLABLE,
    ERROR_MISSING_PARAMS,
    ERROR_UNKNOWN_PARAMS,
    FORMAT_PATH,
    JSON_ADDITIONAL_PROPERTIES_KEY,
    JSON_ANY_OF_KEY,
    JSON_DEFAULT_KEY,
    JSON_ENUM_KEY,
    JSON_FORMAT_KEY,
    JSON_ITEMS_KEY,
    JSON_PROPERTIES_KEY,
    JSON_REQUIRED_KEY,
    JSON_TYPE_KEY,
    TYPE_ARRAY,
    TYPE_BOOLEAN,
    TYPE_INTEGER,
    TYPE_NULL,
    TYPE_NUMBER,
    TYPE_OBJECT,
    TYPE_STRING,
)
from .serde import jsonable_spec


def signature_schema(obj: object) -> JsonObject:
    if not callable(obj):
        raise TypeError(ERROR_COMPONENT_CALLABLE)

    hints = get_type_hints(obj)
    properties: JsonObject = {}
    required: list[JsonValue] = []

    for parameter in keyword_only_parameters(obj).values():
        annotation = hints.get(parameter.name, parameter.annotation)
        schema = annotation_schema(annotation)

        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
        else:
            schema[JSON_DEFAULT_KEY] = jsonable_spec(parameter.default)

        properties[parameter.name] = schema

    return {
        JSON_TYPE_KEY: TYPE_OBJECT,
        JSON_PROPERTIES_KEY: properties,
        JSON_REQUIRED_KEY: required,
        JSON_ADDITIONAL_PROPERTIES_KEY: False,
    }


def annotation_schema(annotation: object) -> JsonObject:
    if annotation is inspect.Parameter.empty or annotation is object:
        return {}

    primitive = primitive_annotation_schema(annotation)
    if primitive is not None:
        return primitive

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        return {JSON_ENUM_KEY: [jsonable_spec(value) for value in args]}

    if origin in (list, tuple):
        return {
            JSON_TYPE_KEY: TYPE_ARRAY,
            JSON_ITEMS_KEY: annotation_schema(args[0]) if args else {},
        }

    if origin in (dict, Mapping):
        return {
            JSON_TYPE_KEY: TYPE_OBJECT,
            JSON_ADDITIONAL_PROPERTIES_KEY: annotation_schema(args[1])
            if len(args) == 2
            else {},
        }

    if is_optional_args(args):
        return {
            JSON_ANY_OF_KEY: [
                *(annotation_schema(arg) for arg in args if arg is not type(None)),
                {JSON_TYPE_KEY: TYPE_NULL},
            ]
        }

    return {}


def primitive_annotation_schema(annotation: object) -> JsonObject | None:
    if annotation is str:
        return {JSON_TYPE_KEY: TYPE_STRING}
    if annotation is bool:
        return {JSON_TYPE_KEY: TYPE_BOOLEAN}
    if annotation is int:
        return {JSON_TYPE_KEY: TYPE_INTEGER}
    if annotation is float:
        return {JSON_TYPE_KEY: TYPE_NUMBER}
    if annotation is Path:
        return {JSON_TYPE_KEY: TYPE_STRING, JSON_FORMAT_KEY: FORMAT_PATH}
    return None


def validate_signature_params(
    factory: object,
    params: Mapping[str, object],
) -> dict[str, object]:
    if not callable(factory):
        raise TypeError(ERROR_COMPONENT_FACTORY_CALLABLE)

    public = keyword_only_parameters(factory)
    unknown = sorted(set(params) - set(public))
    if unknown:
        raise ValueError(ERROR_UNKNOWN_PARAMS.format(unknown=unknown))

    missing = [
        name
        for name, parameter in public.items()
        if parameter.default is inspect.Parameter.empty and name not in params
    ]
    if missing:
        raise ValueError(ERROR_MISSING_PARAMS.format(missing=missing))

    hints = get_type_hints(factory)
    return {
        name: coerce_param(hints.get(name, public[name].annotation), value)
        for name, value in params.items()
    }


def keyword_only_parameters(obj: object) -> dict[str, inspect.Parameter]:
    return {
        parameter.name: parameter
        for parameter in inspect.signature(cast(Callable[..., object], obj)).parameters.values()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    }


def coerce_param(annotation: object, value: object) -> object:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation is Path and isinstance(value, str):
        return Path(value)

    if origin is tuple and isinstance(value, list | tuple):
        item_type = args[0] if args and args[-1] is Ellipsis else object
        return tuple(coerce_param(item_type, item) for item in value)

    if origin is list and isinstance(value, list | tuple):
        item_type = args[0] if args else object
        return [coerce_param(item_type, item) for item in value]

    if is_optional_args(args) and value is not None:
        target = next(candidate for candidate in args if candidate is not type(None))
        return coerce_param(target, value)

    return value


def is_optional_args(args: tuple[object, ...]) -> bool:
    return type(None) in args
