from pathlib import Path


def object_path(store_root: Path, sha: str) -> Path:
    return store_root / "objects" / sha[:2] / sha[2:]


def metadata_path(store_root: Path, kind: str, name: str) -> Path:
    return store_root / kind / f"{name}.yaml"


def alias_path(store_root: Path, kind: str, name: str, alias: str) -> Path:
    return store_root / kind / name / alias
