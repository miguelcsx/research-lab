"""External workspace materialization helpers."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import cast

from rlab.external import ExternalPath

from .constants import (
    DIR_RESOURCES,
    DIR_WORKSPACES,
    ERROR_WORKSPACE_SOURCE,
    KEY_NAME,
    KEY_PATH,
)
from .paths import safe_external_name, safe_relative_path


def materialize_external_workspace(
    *,
    project_root: Path,
    cache_dir: Path,
    run_outputs: Path,
    name: str,
    source_param: str,
    default_source: str,
    ignored: tuple[str, ...],
    cached: tuple[ExternalPath, ...],
    outputs: tuple[ExternalPath, ...],
    params: object,
) -> Path:
    from collections.abc import Mapping

    external_root = run_outputs.parent
    workspace = external_root / "workspace"
    run_outputs.mkdir(parents=True, exist_ok=True)

    if workspace.exists():
        return workspace

    source_value = (
        params.get(source_param, default_source)
        if isinstance(params, Mapping)
        else default_source
    )
    source = _resolve_project_path(project_root, str(source_value))
    if not source.is_dir():
        raise FileNotFoundError(ERROR_WORKSPACE_SOURCE.format(path=source))

    cache_root = cache_dir / safe_external_name(name)
    excluded = tuple(path.path for path in (*cached, *outputs))
    cached_workspace = (
        cache_root / DIR_WORKSPACES / workspace_fingerprint(source, ignored, excluded)
    )

    if not cached_workspace.exists():
        copy_workspace(source, cached_workspace, ignored, excluded)

    if not workspace.exists():
        shutil.copytree(cached_workspace, workspace, symlinks=True)

    link_cached_paths(source, workspace, cache_root, cached)
    link_output_paths(workspace, run_outputs, outputs)
    return workspace


def workspace_fingerprint(
    source: Path,
    ignored: tuple[str, ...],
    excluded: tuple[str, ...],
) -> str:
    digest = hashlib.sha256()
    ignored_names = set(ignored)
    excluded_paths = {safe_relative_path(path) for path in excluded}

    for root, directories, filenames in os.walk(source):
        root_path = Path(root)
        relative_root = root_path.relative_to(source)
        directories[:] = sorted(
            name
            for name in directories
            if name not in ignored_names and relative_root / name not in excluded_paths
        )

        for filename in sorted(name for name in filenames if name not in ignored_names):
            path = root_path / filename
            relative = path.relative_to(source)
            if relative in excluded_paths:
                continue

            stat = path.stat()
            digest.update(f"{relative.as_posix()}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())

    return digest.hexdigest()


def copy_workspace(
    source: Path,
    destination: Path,
    ignored: tuple[str, ...],
    excluded: tuple[str, ...],
) -> None:
    ignored_names = set(ignored)
    excluded_paths = {safe_relative_path(path) for path in excluded}

    def ignore(directory: str, names: list[str]) -> set[str]:
        relative_root = Path(directory).relative_to(source)
        return {
            name
            for name in names
            if name in ignored_names or relative_root / name in excluded_paths
        }

    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)

    if temporary.exists():
        shutil.rmtree(temporary)

    shutil.copytree(source, temporary, symlinks=True, ignore=ignore)
    promote_workspace(temporary, destination)


def promote_workspace(temporary: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(temporary)
        return

    try:
        temporary.rename(destination)
    except OSError:
        if destination.exists():
            shutil.rmtree(temporary)
            return
        raise


def link_cached_paths(
    source: Path,
    workspace: Path,
    cache_root: Path,
    paths: tuple[ExternalPath, ...],
) -> None:
    for external_path in paths:
        name = str(getattr(external_path, KEY_NAME))
        relative = safe_relative_path(str(getattr(external_path, KEY_PATH)))
        target = cache_root / DIR_RESOURCES / safe_external_name(name)
        source_path = source / relative

        if not target.exists():
            copy_or_mkdir(source_path, target)

        replace_with_symlink(workspace / relative, target)


def link_output_paths(
    workspace: Path,
    outputs: Path,
    paths: tuple[ExternalPath, ...],
) -> None:
    for external_path in paths:
        relative = safe_relative_path(str(getattr(external_path, KEY_PATH)))
        name = safe_relative_path(str(getattr(external_path, KEY_NAME)))
        target = outputs / name
        target.mkdir(parents=True, exist_ok=True)
        replace_with_symlink(workspace / relative, target)


def copy_or_mkdir(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, symlinks=True)
        return

    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return

    target.mkdir(parents=True, exist_ok=True)


def replace_with_symlink(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)

    if link.is_symlink() and link.resolve() == target.resolve():
        return

    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.exists():
        shutil.rmtree(link)

    link.symlink_to(target, target_is_directory=target.is_dir())


def _resolve_project_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate
