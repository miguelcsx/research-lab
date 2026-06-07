import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

from rlab.benchmarks.external import ExternalBenchmark
from rlab.benchmarks.runner import execute_benchmark
from rlab.cli import templates
from rlab.config.models import ReproducibilityConfig
from rlab.constants import EntryKind
from rlab.context.factory import build_runtime
from rlab.evaluations.runner import execute_suite
from rlab.external import ExternalCommand, ExternalEvaluation
from rlab.registry.decorators import register
from rlab.reproducibility.capture import capture_reproducibility
from rlab.reproducibility.diff import environment_diff
from rlab.reproducibility.service import reproduce
from rlab.runs.session import RunSession


def test_reproducibility_capture_variants(project: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    capture_reproducibility(
        project,
        run_dir,
        ReproducibilityConfig(
            capture_git=False,
            capture_diff=False,
            capture_env=False,
            capture_packages=False,
            capture_lockfile=False,
            capture_command=False,
            capture_data_manifests=False,
        ),
        ("rlab",),
    )
    assert tuple(run_dir.iterdir()) == ()
    assert environment_diff(run_dir) == {}
    (run_dir / "env.json").write_text(
        json.dumps({"python": "different", "executable": "x", "platform": "x"})
    )
    assert environment_diff(run_dir)


def test_runner_error_branches(project: Path) -> None:
    runtime = build_runtime(project)

    def invalid(target: object, context: object) -> str:
        del target, context
        return "invalid"

    register(
        runtime.registry,
        EntryKind.BENCHMARK,
        "project.invalid",
        invalid,
        target_kind="tokenizer",
    )
    with pytest.raises(TypeError):
        execute_benchmark(
            runtime,
            "tokenizer:project.byte",
            "project.invalid",
        )
    session = RunSession(runtime, "unsupported", "unsupported", {})
    session.start()
    session.complete({})
    with pytest.raises(ValueError):
        reproduce(runtime, session.layout.root)
    with pytest.raises(TypeError):
        execute_suite(runtime, "project.quick", "hf:remote/model")
    external = ExternalEvaluation(
        name="x",
        version="1",
        command=ExternalCommand(args=("echo", "x")),
        parser="json",
        output=Path("x"),
    )
    assert ExternalBenchmark(target_kind="model", evaluation=external).target_kind == "model"


def test_project_locking(project: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rlab.cli.templates.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr=""),
    )
    templates.lock_project(project)
    monkeypatch.setattr(
        "rlab.cli.templates.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="lock failed"),
    )
    with pytest.raises(RuntimeError, match="lock failed"):
        templates.lock_project(project)


def test_reproduction_modes(
    project: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runtime = build_runtime(project)
    source = RunSession(runtime, "experiment", "source", {"path": "missing.py"})
    source.start()
    source.complete({})
    with pytest.raises(RuntimeError, match="remote and commit"):
        reproduce(runtime, source.layout.root, checkout=True)
    with pytest.raises(RuntimeError, match="docker_image"):
        reproduce(runtime, source.layout.root, container=True)
    monkeypatch.setattr(
        "rlab.reproducibility.service.git_snapshot",
        lambda _root: {"commit": None, "dirty": True},
    )
    with pytest.raises(RuntimeError, match="clean Git"):
        reproduce(runtime, source.layout.root, strict=True, use_current_env=True)
