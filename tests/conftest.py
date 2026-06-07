from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.project.templates import write_project


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return write_project(tmp_path, "project", template="ai")


@pytest.fixture
def basic_project(tmp_path: Path) -> Path:
    return write_project(tmp_path, "project", template="basic")


@pytest.fixture
def runtime(project: Path) -> RuntimeContext:
    return build_runtime(project)


@pytest.fixture
def run_root(tmp_path: Path) -> Path:
    path = tmp_path / "run_001"
    path.mkdir()
    return path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("WANDB_API_KEY", raising=False)
    yield
