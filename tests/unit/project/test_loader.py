from __future__ import annotations

from pathlib import Path

from rlab.context.factory import build_runtime
from rlab.project.loader import load_modules
from rlab.project.modules import ModulesConfig
from rlab.project.root import find_project_root
from rlab.project.templates import write_project
from rlab.registry.context import using_registry
from rlab.registry.store import Registry
from tests.helpers.files import write_module


def test_find_project_root(tmp_path: Path) -> None:
    (tmp_path / "lab.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    subdir = tmp_path / "experiments"
    subdir.mkdir()
    assert find_project_root(tmp_path) == tmp_path
    assert find_project_root(subdir) == tmp_path
    assert find_project_root(tmp_path / "missing") is None or isinstance(
        find_project_root(tmp_path / "missing"), Path
    )


def test_load_modules_success_and_failure(tmp_path: Path) -> None:
    write_module(tmp_path, "my_module", "# empty module\n")
    registry = Registry()
    with using_registry(registry):
        success = load_modules(tmp_path, ("my_module",))
        failure = load_modules(tmp_path, ("nonexistent_xyz_module",))

    assert success[0].loaded
    assert not failure[0].loaded
    assert failure[0].error


def test_modules_config_model() -> None:
    assert ModulesConfig().load == ()
    assert ModulesConfig(load=("components.models", "benchmarks.custom")).load == (
        "components.models",
        "benchmarks.custom",
    )


def test_write_project_templates(tmp_path: Path) -> None:
    basic = write_project(tmp_path, "basic_project", template="basic")
    assert (basic / "lab.toml").exists()
    assert (basic / "pyproject.toml").exists()
    assert (basic / "experiments").exists()

    ai = write_project(tmp_path, "ai_project", template="ai")
    assert (ai / "components" / "tokenizers.py").exists()
    assert (ai / "benchmarks" / "custom.py").exists()
    lab_toml = (ai / "lab.toml").read_text(encoding="utf-8")
    assert "[modules]" in lab_toml
    assert "[adapters]" not in lab_toml


def test_build_runtime_loads_project_modules(basic_project: Path) -> None:
    assert build_runtime(basic_project).registry is not None
