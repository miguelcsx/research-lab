from pathlib import Path

import yaml


class ManifestValidationError:
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate_manifest(path: Path) -> tuple[ManifestValidationError, ...]:
    """Validate a manifest YAML file against its declared kind."""
    if not path.exists():
        return (ManifestValidationError(path, "file not found"),)

    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError) as exc:
        return (ManifestValidationError(path, f"YAML parse error: {exc}"),)

    kind = data.get("kind", "")
    errors: list[ManifestValidationError] = []

    required_fields = {
        "dataset": ["name", "version"],
        "model": ["name", "version"],
        "artifact": ["name", "version", "kind"],
        "run": ["name", "operation", "status"],
    }

    for field in required_fields.get(kind, []):
        if field not in data:
            errors.append(ManifestValidationError(path, f"missing required field: {field!r}"))

    return tuple(errors)
