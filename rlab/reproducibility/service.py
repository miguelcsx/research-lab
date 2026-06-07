import json
import shlex
from pathlib import Path
from typing import cast

from rlab.benchmarks.service import run_benchmark
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.service import run_evaluation
from rlab.experiments.service import run_experiment
from rlab.external.repo import checkout_repository
from rlab.external.runner import DockerRunner
from rlab.reproducibility.diff import environment_diff
from rlab.reproducibility.git import git_snapshot
from rlab.runs.reader import RunReader


def reproduction_plan(run_dir: Path) -> tuple[str, ...]:
    command = run_dir / "command.txt"
    return tuple(shlex.split(command.read_text())) if command.exists() else ()


def _recorded_git(run_dir: Path) -> dict[str, object]:
    path = run_dir / "git.json"
    return cast(dict[str, object], json.loads(path.read_text())) if path.exists() else {}


def _strict_check(
    runtime: RuntimeContext,
    run_dir: Path,
    *,
    allow_dirty: bool,
    use_current_env: bool,
) -> None:
    if not use_current_env and environment_diff(run_dir):
        raise RuntimeError("Current environment differs from the recorded run")
    recorded = _recorded_git(run_dir)
    current = git_snapshot(runtime.paths.root)
    if not allow_dirty and (recorded.get("dirty") or current.get("dirty")):
        raise RuntimeError("Strict reproduction requires clean Git worktrees")
    if recorded.get("commit") and recorded["commit"] != current.get("commit"):
        raise RuntimeError("Current Git commit differs from the recorded run")


def _checkout_runtime(runtime: RuntimeContext, run_dir: Path) -> RuntimeContext:
    recorded = _recorded_git(run_dir)
    remote, commit = recorded.get("remote"), recorded.get("commit")
    if not isinstance(remote, str) or not isinstance(commit, str):
        raise RuntimeError("Recorded Git remote and commit are required for checkout")
    root = checkout_repository(remote, commit, runtime.paths.cache / "reproductions")
    return build_runtime(root)


def _container_replay(runtime: RuntimeContext, run_dir: Path) -> Path:
    image = runtime.config.launcher.docker_image
    if image is None:
        raise RuntimeError("launcher.docker_image is required for container reproduction")
    plan = reproduction_plan(run_dir)
    command = DockerRunner().command(
        image,
        *plan,
        mounts=((runtime.paths.root, "/workspace"),),
    )
    DockerRunner().run(command, runtime.paths.root)
    return run_dir


def reproduce(  # noqa: PLR0913
    runtime: RuntimeContext,
    run_dir: Path,
    *,
    dry_run: bool = False,
    strict: bool = False,
    allow_dirty: bool = False,
    checkout: bool = False,
    use_current_env: bool = False,
    container: bool = False,
) -> Path | tuple[str, ...]:
    if container:
        return _container_replay(runtime, run_dir)
    original_root = runtime.paths.root
    reader = RunReader(run_dir)
    manifest = reader.manifest()
    if dry_run:
        return reproduction_plan(run_dir)
    if checkout:
        runtime = _checkout_runtime(runtime, run_dir)
    if strict:
        _strict_check(
            runtime,
            run_dir,
            allow_dirty=allow_dirty,
            use_current_env=use_current_env,
        )
    params = manifest.parameters
    if manifest.operation == "benchmark":
        return run_benchmark(
            runtime,
            str(params["target"]),
            str(params["benchmark"]),
            data=str(params["data"]) if params.get("data") else None,
        )
    if manifest.operation == "evaluation":
        return run_evaluation(runtime, str(params["suite"]), str(params["model"]))
    if manifest.operation == "experiment":
        path = Path(str(params["path"]))
        if runtime.paths.root != original_root:
            path = runtime.paths.root / path.relative_to(original_root)
        return cast(Path, run_experiment(runtime, path))
    raise ValueError(f"Run operation {manifest.operation!r} is not reproducible")
