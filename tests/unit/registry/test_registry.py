from __future__ import annotations

from pathlib import Path

import pytest

from rlab.constants import EntryKind
from rlab.errors import RegistryConflictError, RegistryError
from rlab.project.loader import ModuleLoadResult, load_modules
from rlab.project.modules import failed_modules, loaded_modules
from rlab.project.validation import validate_project
from rlab.registry.context import current_registry, using_registry
from rlab.registry.decorators import register
from rlab.registry.keys import ComponentKey, RegistryKey
from rlab.registry.namespaces import qualified_name, validate_name
from rlab.registry.store import Registry
from rlab.registry.validation import validate_signature, validate_version


def test_registry_records_conflicts_clear_and_lookup_errors() -> None:
    registry = Registry()

    def first() -> None: ...
    def second() -> None: ...

    register(registry, EntryKind.EXPERIMENT, "team.first", first)
    assert registry.get(EntryKind.EXPERIMENT, "team.first").namespace == "team"
    assert registry.list(EntryKind.EXPERIMENT)[0].value is first
    with pytest.raises(RegistryConflictError):
        register(registry, EntryKind.EXPERIMENT, "team.first", second)
    with pytest.raises(RegistryError, match="available"):
        registry.get(EntryKind.SUITE, "missing")
    registry.clear()
    assert registry.list() == ()
    assert registry.conflicts() == ()


def test_registry_keys_names_versions_and_signature_validation() -> None:
    assert str(RegistryKey(kind=EntryKind.SUITE, name="team.quick")) == "suite:team.quick"
    assert str(ComponentKey(kind="model", name="tiny")) == "model:tiny"
    assert qualified_name("team", "value") == "team.value"
    assert validate_name("tokenizer:team.byte") == "tokenizer:team.byte"
    assert validate_version("1.2.3") == "1.2.3"

    with pytest.raises(ValueError):
        RegistryKey(kind=EntryKind.SUITE, name="bad name")
    with pytest.raises(RegistryError):
        validate_name("bad name")
    with pytest.raises(RegistryError):
        validate_version("v1")

    def bad_benchmark(target: object) -> None:
        del target

    with pytest.raises(RegistryError):
        validate_signature(EntryKind.BENCHMARK, bad_benchmark)


def test_registry_context_restores_previous_registry() -> None:
    custom = Registry()
    original = current_registry()
    with using_registry(custom):
        assert current_registry() is custom
    assert current_registry() is original


def test_module_load_results_and_filters(tmp_path: Path) -> None:
    ok = ModuleLoadResult(name="components.models", loaded=True, registered_kinds=("component",))
    failed = ModuleLoadResult(name="bad.module", loaded=False, error="ImportError")
    assert ok.loaded
    assert failed.error is not None
    assert failed_modules((ok, failed)) == (failed,)
    assert loaded_modules((ok, failed)) == (ok,)

    registry = Registry()
    with using_registry(registry):
        results = load_modules(tmp_path, ("nonexistent_module_xyz",))
    assert not results[0].loaded


def test_validate_project(tmp_path: Path) -> None:
    assert any("lab.toml" in issue.check for issue in validate_project(tmp_path))
    (tmp_path / "lab.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    assert not [issue for issue in validate_project(tmp_path) if issue.severity.value == "error"]
