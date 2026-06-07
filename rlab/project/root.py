from pathlib import Path


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) until lab.toml is found."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / "lab.toml").exists():
            return directory
    return None
