from collections.abc import Mapping
from typing import Any


def data_report(name: str, profile: Mapping[str, Any], checks: Mapping[str, str]) -> str:
    lines = [f"# Dataset {name}", "", "## Profile", ""]
    lines.extend(f"- `{key}`: {value}" for key, value in profile.items())
    lines.extend(("", "## Checks", ""))
    lines.extend(f"- `{key}`: {value}" for key, value in checks.items())
    return "\n".join(lines) + "\n"
