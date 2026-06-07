from pathlib import Path

import pytest

from rlab.config.hydra_adapter import compose_hydra
from rlab.config.loader import load_config
from rlab.config.overrides import apply_overrides, parse_overrides, parse_value
from rlab.config.resolver import resolve_string, resolve_values
from rlab.errors import ConfigError, ReferenceError
from rlab.references.parser import parse_reference
from rlab.references.refs import ReferenceKind


def test_config_loading_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "lab.toml").write_text(
        "[project]\nname='base'\n[paths]\nruns='${project.root}/custom-runs'\n"
    )
    monkeypatch.setenv("RLAB__PROJECT__NAME", "environment")
    config = load_config(tmp_path, ("project.name=cli",))
    assert config.project.name == "cli"
    assert config.paths.runs == tmp_path / "custom-runs"


def test_overrides_and_resolution(tmp_path: Path) -> None:
    assert parse_value("true") is True
    assert parse_value("word") == "word"
    assert parse_overrides(("a.b=1",)) == {"a.b": 1}
    assert apply_overrides({"a": {"b": 0}}, {"a.b": 2}) == {"a": {"b": 2}}
    assert resolve_string("${project.root}/x", project_root=tmp_path) == f"{tmp_path}/x"
    assert resolve_values({"x": ["${project.root}"]}, project_root=tmp_path) == {
        "x": [str(tmp_path)]
    }
    with pytest.raises(ConfigError):
        parse_overrides(("invalid",))
    with pytest.raises(ConfigError):
        apply_overrides({"a": 1}, {"a.b": 2})


def test_invalid_config_and_optional_hydra(tmp_path: Path) -> None:
    (tmp_path / "lab.toml").write_text("[plugins]\nautoload='not-bool'\n")
    with pytest.raises(ConfigError):
        load_config(tmp_path)
    with pytest.raises(ConfigError, match="Hydra"):
        compose_hydra(())


@pytest.mark.parametrize(
    ("text", "kind", "component_kind", "alias"),
    [
        ("hf:gpt2", ReferenceKind.HF, None, None),
        ("tokenizer:byte", ReferenceKind.COMPONENT, "tokenizer", None),
        ("artifact:model/name@best", ReferenceKind.ARTIFACT, None, "best"),
        ("run:abc", ReferenceKind.RUN, None, None),
    ],
)
def test_reference_parser(
    text: str,
    kind: ReferenceKind,
    component_kind: str | None,
    alias: str | None,
) -> None:
    reference = parse_reference(text)
    assert reference.kind is kind
    assert reference.component_kind == component_kind
    assert reference.alias == alias
    assert str(reference) == text


@pytest.mark.parametrize("text", ["missing", "artifact:name", "!bad:value"])
def test_invalid_references(text: str) -> None:
    with pytest.raises(ReferenceError):
        parse_reference(text)
