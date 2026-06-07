from __future__ import annotations

from pathlib import Path

import pytest

from rlab.cli.commands import init as init_command
from tests.helpers.cli import assert_success, invoke_cli, invoke_json


def test_help_renders() -> None:
    assert_success(invoke_cli(Path.cwd(), "--help"))


def test_init_project_and_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        init_command,
        "lock_project",
        lambda project: (project / "uv.lock").write_text("version = 1\n", encoding="utf-8"),
    )
    project = tmp_path / "generated"
    assert_success(invoke_cli(tmp_path, "init", "project", project.name))
    assert (project / "lab.toml").exists()
    assert (project / "uv.lock").exists()

    for template_kind in ("benchmark", "experiment", "workflow"):
        assert_success(invoke_cli(tmp_path, "init", template_kind, f"{template_kind}_template"))


def test_project_diagnostics_commands(project: Path) -> None:
    for args in (
        ("doctor",),
        ("config", "validate"),
        ("config", "show"),
        ("config", "paths"),
        ("discover",),
        ("status",),
        ("modules", "list"),
        ("modules", "doctor"),
        ("modules", "reload"),
    ):
        assert_success(invoke_cli(project, *args))


def test_discover_supports_json_output(project: Path) -> None:
    assert_success(invoke_json(project, "discover", "benchmarks"))
