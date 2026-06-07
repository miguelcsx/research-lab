from collections.abc import Callable
from pathlib import Path
from typing import Never

import pytest

from rlab.constants import EntryKind
from rlab.plugins.loader import load_installed_plugins, load_project_plugins
from rlab.registry.decorators import register as add
from rlab.registry.store import Registry


class FakeEntryPoint:
    name = "fake"
    value = "fake:register"
    module = "fake"
    dist = None

    def load(self) -> Callable[[Registry], None]:
        def register(registry: Registry) -> None:
            def suite() -> None:
                pass

            add(registry, EntryKind.SUITE, "plugin.quick", suite, plugin="fake")

        return register


class BrokenEntryPoint(FakeEntryPoint):
    name = "broken"

    def load(self) -> Never:
        raise ImportError("broken")


def test_installed_plugin_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rlab.plugins.loader.installed_entrypoints",
        lambda: (FakeEntryPoint(), BrokenEntryPoint()),
    )
    registry = Registry()
    metadata = load_installed_plugins(registry)
    assert metadata[0].loaded
    assert metadata[1].error == "broken"
    assert registry.get(EntryKind.SUITE, "plugin.quick").plugin == "fake"


def test_project_plugin_loading(project: Path) -> None:
    paths = load_project_plugins(
        project,
        type("Config", (), {"modules": ("components",)})(),
    )
    assert any(path.name == "tokenizers.py" for path in paths)
