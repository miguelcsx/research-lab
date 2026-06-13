"""Runner path and artifact-name helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .constants import (
    ARTIFACT_HASH_LEN,
    ARTIFACT_PREFIX_LEN,
    ERROR_EXTERNAL_NAME,
    ERROR_EXTERNAL_PATH,
    ERROR_OUTPUT_PATH,
    MAX_ARTIFACT_NAME_LEN,
    PATH_PARENT,
    PATH_SEPARATORS,
)


def safe_external_name(name: str) -> str:
    value = str(name).strip()
    if value and not any(part in value for part in PATH_SEPARATORS):
        return value
    raise ValueError(ERROR_EXTERNAL_NAME.format(name=name))


def bounded_artifact_name(command_name: str, stem: str) -> str:
    value = f"{command_name}.{stem}"
    if len(value) <= MAX_ARTIFACT_NAME_LEN:
        return value

    digest = hashlib.sha256(value.encode()).hexdigest()[:ARTIFACT_HASH_LEN]
    return f"{value[:ARTIFACT_PREFIX_LEN]}.{digest}"


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if not path.parts or path.is_absolute() or PATH_PARENT in path.parts:
        raise ValueError(ERROR_EXTERNAL_PATH.format(path=value))
    return path


def safe_output_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or PATH_PARENT in path.parts:
        raise ValueError(ERROR_OUTPUT_PATH)
    return path


def resolve_project_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate


def files_below(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def artifact_stem(path: Path, root: Path) -> str:
    return path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
