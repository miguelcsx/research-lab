from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.constants import Severity


class ProjectIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    check: str
    severity: Severity
    message: str
    fix: str | None = None


def validate_project(root: Path) -> tuple[ProjectIssue, ...]:
    """Return all issues found in a project directory."""
    issues: list[ProjectIssue] = []

    def issue(check: str, severity: Severity, message: str, fix: str | None = None) -> None:
        issues.append(ProjectIssue(check=check, severity=severity, message=message, fix=fix))

    if not (root / "lab.toml").exists():
        issue("lab.toml", Severity.ERROR, "lab.toml not found", "Run `rlab init project <name>`")

    if not (root / "pyproject.toml").exists():
        issue("pyproject.toml", Severity.WARNING, "pyproject.toml not found")

    if not (root / ".git").exists():
        issue("git", Severity.WARNING, "Not a git repository", "Run `git init`")

    runs_dir = root / "runs"
    if runs_dir.exists() and not runs_dir.is_dir():
        issue("runs", Severity.ERROR, "runs/ exists but is not a directory")

    return tuple(issues)
