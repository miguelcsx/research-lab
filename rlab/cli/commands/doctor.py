import shutil
import subprocess
from typing import Any

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState


def command(ctx: typer.Context) -> None:  # noqa: PLR0915
    """Run all project health checks."""
    state: CliState = ctx.obj

    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, note: str = "") -> None:
        checks.append({"check": name, "ok": passed, "note": note})

    def warn(name: str, note: str = "") -> None:
        checks.append({"check": name, "ok": True, "note": f"⚠ {note}" if note else "⚠ warning"})

    # Basic files
    check("lab.toml", (state.root / "lab.toml").exists())
    check("pyproject.toml", (state.root / "pyproject.toml").exists())

    # Runtime paths
    runtime = None
    try:
        runtime = state.runtime()
        check("config loads", True)
        check("runs writable", runtime.paths.runs.exists())
        check("artifacts writable", runtime.paths.artifacts.exists())
    except Exception as exc:
        check("config loads", False, str(exc)[:60])

    # Tools
    check("git", shutil.which("git") is not None)
    check("uv", shutil.which("uv") is not None)

    # Git repo (warning only — not a hard failure)
    if shutil.which("git") is None:
        warn("git repo", "git not available")
    else:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=state.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            warn("git repo", "not a git repository")
        else:
            check("git repo", True)

    # Module loading
    if runtime is not None:
        from rlab.project.loader import load_modules
        from rlab.registry.store import Registry

        registry = Registry()
        results = load_modules(state.root, runtime.config.modules.load, registry=registry)
        failed = [r for r in results if not r.loaded]
        check(
            "modules",
            len(failed) == 0,
            (
                f"{len(results)} declared, {len(failed)} failed"
                if failed
                else f"{len(results)} loaded"
            ),
        )

    # External tool availability
    _check_external_tools(check, warn)

    # Project validation (warnings only for non-errors)
    from rlab.project.validation import validate_project

    issues = validate_project(state.root)
    errors = [i for i in issues if i.severity.value == "error"]
    warnings_list = [i for i in issues if i.severity.value != "error"]
    if errors:
        check("project validation", False, f"{len(errors)} error(s)")
    elif warnings_list:
        warn("project validation", f"{len(warnings_list)} warning(s)")
    else:
        check("project validation", True)

    state.console.print(table("rlab doctor", checks))

    failed_checks = [c for c in checks if not c["ok"]]
    if failed_checks:
        state.console.print(f"\n[red]{len(failed_checks)} check(s) failed.[/red]")
        raise typer.Exit(1)
    else:
        state.console.print("\n[green]All checks passed.[/green]")


def _check_external_tools(check: Any, warn: Any) -> None:
    """Check common external research tools."""
    tools = {
        "docker": shutil.which("docker") is not None,
        "conda": shutil.which("conda") is not None,
        "pytest": shutil.which("pytest") is not None,
    }
    for name, available in tools.items():
        if available:
            check(name, True)
        else:
            warn(name, "not found in PATH")
