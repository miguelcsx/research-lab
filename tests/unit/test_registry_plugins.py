from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

from rlab.constants import EntryKind
from rlab.errors import RegistryConflictError, RegistryError
from rlab.plugins.entrypoints import metadata_for
from rlab.plugins.loader import plugin_failures
from rlab.plugins.metadata import PluginMetadata
from rlab.registry.context import current_registry, using_registry
from rlab.registry.decorators import register
from rlab.registry.keys import ComponentKey, RegistryKey
from rlab.registry.namespaces import qualified_name, validate_name
from rlab.registry.store import Registry
from rlab.registry.validation import validate_signature, validate_version


def test_registry_records_and_overrides(tmp_path: Path) -> None:
    registry = Registry()

    def first() -> None:
        pass

    def second() -> None:
        pass

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


def test_registry_keys_names_and_validation() -> None:
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


def test_registry_context() -> None:
    custom = Registry()
    original = current_registry()
    with using_registry(custom):
        assert current_registry() is custom
    assert current_registry() is original


def test_plugin_metadata_and_failures() -> None:
    entrypoint = EntryPoint(name="demo", value="package.module:register", group="rlab.plugins")
    metadata = metadata_for(entrypoint)
    assert metadata.name == "demo"
    failed = metadata.model_copy(update={"error": "broken"})
    assert plugin_failures((metadata, failed)) == (failed,)
    assert PluginMetadata(name="x", version="1", package="x", entrypoint="x:y").loaded is False
