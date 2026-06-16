"""Functional access to Rust-owned project and experiment configuration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeVar, overload

from rlab._rlab import (
    diff_config_documents,
    list_config_documents,
    resolve_config_document,
    validate_config_documents,
)
from rlab._documents import apply_overrides, decode_object, encode_overrides, validate_model
from rlab._typing import JsonObject, JsonValue

DEFAULT_SUFFIX: Final = ".yaml"
DEFAULT_REQUIRE_EXPLICIT_PATHS: Final = True
DOCUMENT_LABEL: Final = "configuration"
ModelT = TypeVar("ModelT")

__all__ = [
    "apply_overrides",
    "diff_configs",
    "list_configs",
    "resolve_config",
    "validate_configs",
]


@overload
def resolve_config(
    root: str | Path,
    name: str,
    *,
    overrides: Mapping[str, JsonValue] | None = None,
    suffix: str = DEFAULT_SUFFIX,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject: ...


@overload
def resolve_config(
    root: str | Path,
    name: str,
    *,
    model: type[ModelT],
    overrides: Mapping[str, JsonValue] | None = None,
    suffix: str = DEFAULT_SUFFIX,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> ModelT: ...


def resolve_config(
    root: str | Path,
    name: str,
    *,
    model: type[ModelT] | None = None,
    overrides: Mapping[str, JsonValue] | None = None,
    suffix: str = DEFAULT_SUFFIX,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject | ModelT:
    document = decode_object(
        resolve_config_document(Path(root), name, encode_overrides(overrides), suffix, require_explicit_paths),
        DOCUMENT_LABEL,
    )
    return document if model is None else validate_model(model, document)


def list_configs(root: str | Path, *, suffix: str = DEFAULT_SUFFIX) -> tuple[str, ...]:
    return tuple(list_config_documents(Path(root), suffix))


def validate_configs(
    root: str | Path, *, suffix: str = DEFAULT_SUFFIX
) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in decode_object(
            validate_config_documents(Path(root), suffix),
            DOCUMENT_LABEL,
        ).items()
    }


def diff_configs(left: JsonObject, right: JsonObject) -> JsonObject:
    return decode_object(
        diff_config_documents(
            encode_overrides(left),
            encode_overrides(right),
        ),
        DOCUMENT_LABEL,
    )
