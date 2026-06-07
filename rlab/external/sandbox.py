import os
from collections.abc import Mapping
from pathlib import Path


def sandbox_environment(extra: Mapping[str, str]) -> dict[str, str]:
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CUDA_VISIBLE_DEVICES")
    return {**{key: os.environ[key] for key in allowed if key in os.environ}, **extra}


def safe_workdir(root: Path, requested: Path | None) -> Path:
    path = (requested or root).resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"External working directory does not exist: {path}")
    return path
