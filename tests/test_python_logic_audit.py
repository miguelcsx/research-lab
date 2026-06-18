from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_component_facade_does_not_shadow_native_contract_logic() -> None:
    source = _source("python/rlab/components.py")
    native_source = _source("crates/rlab-py/src/py_components.rs")
    runner_source = _source("python/rlab/_runner.py")

    forbidden = [
        "class ComponentSpec",
        "class Requirements",
        "class ComponentContract",
        "def missing_requirements",
        "def collect_requirements",
        "def collect_contracts",
    ]

    assert "from rlab._rlab import" in source
    for pattern in forbidden:
        assert pattern not in source
    assert 'map.get("reference")' not in native_source
    assert 'map.get("name")' not in native_source
    assert 'value.get("reference")' not in runner_source
    assert 'value.get("name")' not in runner_source
    assert "class _ChildContext" not in runner_source
    assert "def run(self, target:" not in runner_source


def test_cache_facade_does_not_reimplement_jsonl_or_hashing() -> None:
    source = _source("python/rlab/cache/__init__.py")

    forbidden = [
        "hashlib",
        "sha256",
        "json.dumps",
        "json.loads",
        "os.replace",
        ".open(",
        "def cache_key",
        "def read_jsonl",
        "def write_jsonl_atomic",
    ]

    assert "from rlab._rlab import" in source
    for pattern in forbidden:
        assert pattern not in source


def test_record_stage_helpers_delegate_to_native_exports() -> None:
    source = _source("python/rlab/data/primitives.py")
    data_init_source = _source("python/rlab/data/__init__.py")

    assert "substitute as _substitute" in source
    assert "classify as _classify" in source
    assert "threshold as _threshold" in source
    assert "return _substitute(field, old, new)" in source
    assert "return _classify(field, dict(labels))" in source
    assert "return _threshold(field, minimum, maximum)" in source
    assert "register_builtins" not in source
    assert "register_builtins" not in data_init_source


def test_top_level_overrides_delegate_to_native_binding() -> None:
    source = _source("python/rlab/__init__.py")
    config_source = _source("python/rlab/config/__init__.py")
    documents_source = _source("python/rlab/_documents.py")

    assert "    apply_overrides," in source
    assert "from .config import apply_overrides" not in source
    assert '"apply_overrides"' not in config_source
    assert "def apply_overrides" not in documents_source


def test_removed_python_logic_modules_and_generated_extension_stay_untracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()

    assert "python/rlab/manifests.py" not in tracked
    assert "python/rlab/overrides.py" not in tracked
    assert not any(path.startswith("python/rlab/") and path.endswith(".so") for path in tracked)
