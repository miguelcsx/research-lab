import json
from collections.abc import Sequence
from pathlib import Path

from rlab.config.models import ReproducibilityConfig
from rlab.reproducibility.command import write_command
from rlab.reproducibility.env import full_environment
from rlab.reproducibility.git import git_diff, git_snapshot
from rlab.reproducibility.lockfile import capture_project_files


def capture_reproducibility(
    root: Path,
    run_dir: Path,
    config: ReproducibilityConfig,
    command: Sequence[str],
) -> None:
    if config.capture_command:
        write_command(run_dir / "command.txt", command)
    if config.capture_git:
        (run_dir / "git.json").write_text(json.dumps(git_snapshot(root), indent=2) + "\n")
    if config.capture_diff:
        (run_dir / "git.diff").write_text(git_diff(root))
    if config.capture_env:
        environment = full_environment()
        if not config.capture_packages:
            environment.pop("packages", None)
        (run_dir / "env.json").write_text(json.dumps(environment, indent=2) + "\n")
    if config.capture_lockfile:
        capture_project_files(root, run_dir)
