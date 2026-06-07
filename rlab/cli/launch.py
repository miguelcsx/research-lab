import sys
from pathlib import Path

from rlab.cli.state import CliState
from rlab.external.runner import DockerRunner
from rlab.jobs.manager import JobManager
from rlab.jobs.store import JobStore


def launch_run(
    state: CliState,
    launcher: str,
    experiment: Path,
    *,
    only: str | None,
) -> str:
    runtime = state.runtime()
    arguments = (
        "--root",
        str(state.root),
        "run",
        str(experiment),
        "--launcher",
        "local",
        *(("--only", only) if only else ()),
    )
    if launcher == "subprocess":
        command = (sys.executable, "-m", "rlab", *arguments)
    elif launcher == "docker":
        image = runtime.config.launcher.docker_image
        if image is None:
            raise ValueError("launcher.docker_image is required for Docker runs")
        command = (
            DockerRunner()
            .command(
                image,
                "rlab",
                "--root",
                "/workspace",
                "run",
                f"/workspace/{experiment.relative_to(state.root)}",
                "--launcher",
                "local",
                mounts=((state.root, "/workspace"),),
            )
            .args
        )
    else:
        raise ValueError(f"Unsupported launcher {launcher!r}")
    manager = JobManager(
        JobStore(runtime.paths.cache / "jobs.sqlite3"),
        runtime.paths.cache / "jobs" / "logs",
    )
    return manager.start(command, state.root).id
