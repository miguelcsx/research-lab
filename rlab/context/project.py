from pathlib import Path

from rlab.errors import ConfigError


def find_project(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "lab.toml").exists():
            return candidate
    raise ConfigError("No lab.toml found; run 'rlab init project'")
