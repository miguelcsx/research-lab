import os
import re
from pathlib import Path
from typing import Any

VARIABLE = re.compile(r"\$\{([^}]+)}")


def resolve_string(value: str, *, project_root: Path) -> str:
    variables = {"project.root": str(project_root), **os.environ}
    return VARIABLE.sub(lambda match: variables.get(match.group(1), match.group(0)), value)


def resolve_values(value: Any, *, project_root: Path) -> Any:
    if isinstance(value, str):
        return resolve_string(value, project_root=project_root)
    if isinstance(value, list):
        return [resolve_values(item, project_root=project_root) for item in value]
    if isinstance(value, dict):
        return {key: resolve_values(item, project_root=project_root) for key, item in value.items()}
    return value
