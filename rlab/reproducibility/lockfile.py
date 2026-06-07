import shutil
from pathlib import Path


def capture_project_files(root: Path, destination: Path) -> tuple[Path, ...]:
    copied: list[Path] = []
    for name in ("pyproject.toml", "uv.lock", "poetry.lock", "requirements.txt", "lab.toml"):
        source = root / name
        if source.exists():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target)
    return tuple(copied)
