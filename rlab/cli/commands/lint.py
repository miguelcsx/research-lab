from __future__ import annotations

import shutil
import subprocess

import typer

from rlab.cli.state import CliState


def command(ctx: typer.Context) -> None:  # noqa: PLR0912
    """Check project for missing hypotheses, bad metric names, untracked artifacts, etc."""
    state: CliState = ctx.obj
    issues: list[tuple[str, str]] = []

    # Check experiments for missing hypotheses
    experiments_dir = state.root / "experiments"
    if experiments_dir.exists():
        for exp_file in experiments_dir.rglob("*.py"):
            text = exp_file.read_text()
            if "Experiment(" in text and "hypothesis=" not in text:
                issues.append(("warning", f"{exp_file.name}: Experiment missing hypothesis"))
            if "Experiment(" in text and "question=" not in text:
                issues.append(("error", f"{exp_file.name}: Experiment missing question"))

    # Check for runs without manifests
    runs_dir = state.root / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir() and not (run_dir / "run.yaml").exists():
                issues.append(("warning", f"runs/{run_dir.name}: Missing run.yaml"))

    # Check git-ignored large files
    _LARGE_FILE_THRESHOLD = 50 * 1024 * 1024
    if shutil.which("git") is not None:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=state.root,
            capture_output=True,
            text=True,
            check=False,
        )
        for fname in result.stdout.splitlines():
            path = state.root / fname
            if path.exists() and path.stat().st_size > _LARGE_FILE_THRESHOLD:
                size_mb = path.stat().st_size // 1024 // 1024
                issues.append(
                    (
                        "warning",
                        f"{fname}: Untracked large file ({size_mb}MB)",
                    )
                )

    # Check modules declared but missing
    runtime = state.runtime()
    for module_name in runtime.config.modules.load:
        module_path = state.root / module_name.replace(".", "/")
        py_path = state.root / (module_name.replace(".", "/") + ".py")
        if not module_path.exists() and not py_path.exists():
            issues.append(
                (
                    "error",
                    f"Module {module_name!r} declared in lab.toml but file not found",
                )
            )

    if not issues:
        state.console.print("[green]No issues found.[/green]")
        return

    for level, msg in issues:
        color = "red" if level == "error" else "yellow"
        state.console.print(f"[{color}]{level.upper()}[/{color}]: {msg}")

    errors = [i for i in issues if i[0] == "error"]
    if errors:
        raise typer.Exit(1)
