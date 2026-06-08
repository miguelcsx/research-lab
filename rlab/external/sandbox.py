import os
from collections.abc import Mapping
from pathlib import Path

_ALLOWED_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CUDA_VISIBLE_DEVICES")


def sandbox_environment(extra: Mapping[str, str]) -> dict[str, str]:
    return {**{key: os.environ[key] for key in _ALLOWED_ENV if key in os.environ}, **extra}


def safe_workdir(root: Path, requested: Path | None) -> Path:
    path = (requested or root).resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"External working directory does not exist: {path}")
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise ValueError(f"Working directory must be inside project root: {path}")
    return path
