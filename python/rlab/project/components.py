"""Component reference, schema, and build helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from rlab._typing import JsonObject
from rlab.components import ComponentSpec, Requirements

from .constants import (
    ERROR_COMPONENT_PARAMS_MAPPING,
    ERROR_COMPONENT_REFERENCE_FORMAT,
    ERROR_COMPONENT_REFERENCE_MIXED,
    ERROR_COMPONENT_REFERENCE_REQUIRED,
    ERROR_LEGACY_BUILD_SPEC,
    ERROR_SCHEMA_DICT,
    ERROR_SCHEMA_JSON,
    ERROR_SCHEMA_VALIDATE,
    KEY_COMPONENT_KIND,
    KEY_REFERENCE,
    KEY_REQUIREMENTS,
    REFERENCE_SEPARATOR,
    REFERENCE_SEPARATOR_COUNT,
)
from .registry_helpers import validate_identifier


def component_identity(
    reference: str | None,
    kind: str | None,
    name: str | None,
) -> tuple[str, str]:
    if reference is not None:
        if kind is not None or name is not None:
            raise TypeError(ERROR_COMPONENT_REFERENCE_MIXED)
        if reference.count(REFERENCE_SEPARATOR) != REFERENCE_SEPARATOR_COUNT:
            raise ValueError(ERROR_COMPONENT_REFERENCE_FORMAT)
        component_kind, component_name = reference.split(REFERENCE_SEPARATOR, 1)
        validate_identifier(component_kind, component_name)
        return component_kind, component_name

    if kind is None or name is None:
        raise TypeError(ERROR_COMPONENT_REFERENCE_REQUIRED)

    validate_identifier(kind, name)
    return kind, name


def component_metadata(
    kind: str,
    name: str,
    requires: Requirements,
    metadata: Mapping[str, object],
) -> dict[str, object]:
    return {
        **metadata,
        KEY_COMPONENT_KIND: kind,
        KEY_REFERENCE: f"{kind}:{name}",
        KEY_REQUIREMENTS: requires.to_dict(),
    }


def schema_dict(params_schema: type[object], label: str) -> JsonObject:
    schema = getattr(params_schema, "model_json_schema", None)
    if not callable(schema):
        raise TypeError(ERROR_SCHEMA_JSON.format(label=label))

    value = schema()
    if not isinstance(value, dict):
        raise TypeError(ERROR_SCHEMA_DICT.format(label=label))

    return cast(JsonObject, value)


def validate_model_schema(
    schema: type[object],
    params: object,
    kind: str,
    name: str,
) -> object:
    validate = getattr(schema, "model_validate", None)
    if not callable(validate):
        raise TypeError(ERROR_SCHEMA_VALIDATE.format(kind=kind, name=name))
    return validate(params)


def build_parts(
    reference: str,
    spec: ComponentSpec[object] | Mapping[str, object] | None,
) -> tuple[str, str, object]:
    if REFERENCE_SEPARATOR in reference:
        kind, name = reference.split(REFERENCE_SEPARATOR, 1)
        if spec is None:
            return kind, name, {}
        if isinstance(spec, ComponentSpec):
            return kind, name, spec.params
        return kind, name, dict(spec)

    if not isinstance(spec, ComponentSpec):
        raise TypeError(ERROR_LEGACY_BUILD_SPEC)

    return reference, spec.name, spec.params
