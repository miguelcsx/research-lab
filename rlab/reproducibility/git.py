import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(("git", *args), cwd=root, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def git_snapshot(root: Path) -> dict[str, object]:
    return {
        "commit": _git(root, "rev-parse", "HEAD"),
        "branch": _git(root, "branch", "--show-current"),
        "remote": _git(root, "remote", "get-url", "origin"),
        "dirty": bool(_git(root, "status", "--porcelain")),
    }


def git_diff(root: Path) -> str:
    return _git(root, "diff", "--binary", "HEAD") or ""
