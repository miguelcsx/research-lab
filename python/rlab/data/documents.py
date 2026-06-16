"""Functional access to Rust-owned data configuration documents."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeVar, overload

from rlab._rlab import (
    list_data_documents,
    resolve_data_document,
    validate_data_documents,
)
from rlab._documents import decode_object, encode_overrides, validate_model
from rlab._typing import JsonObject, JsonValue

DEFAULT_REQUIRE_EXPLICIT_PATHS: Final = True
DOCUMENT_LABEL: Final = "data document"
ModelT = TypeVar("ModelT")

__all__ = ["list_datasets", "resolve_dataset", "validate_datasets"]


@overload
def resolve_dataset(
    root: str | Path,
    name: str,
    *,
    overrides: Mapping[str, JsonValue] | None = None,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject: ...


@overload
def resolve_dataset(
    root: str | Path,
    name: str,
    *,
    model: type[ModelT],
    overrides: Mapping[str, JsonValue] | None = None,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> ModelT: ...


def resolve_dataset(
    root: str | Path,
    name: str,
    *,
    model: type[ModelT] | None = None,
    overrides: Mapping[str, JsonValue] | None = None,
    require_explicit_paths: bool = DEFAULT_REQUIRE_EXPLICIT_PATHS,
) -> JsonObject | ModelT:
    document = decode_object(
        resolve_data_document(Path(root), name, encode_overrides(overrides), require_explicit_paths),
        DOCUMENT_LABEL,
    )
    return document if model is None else validate_model(model, document)


def list_datasets(root: str | Path) -> tuple[str, ...]:
    return tuple(list_data_documents(Path(root)))


def validate_datasets(root: str | Path) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in decode_object(validate_data_documents(Path(root)), DOCUMENT_LABEL).items()
    }
