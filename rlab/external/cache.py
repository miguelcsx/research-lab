from pathlib import Path


def external_cache(root: Path, name: str, revision: str) -> Path:
    return root / "external" / name / revision
