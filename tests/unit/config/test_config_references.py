from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ConfigDict

from rlab.config.hydra_adapter import compose_hydra
from rlab.config.loader import load_config
from rlab.config.overrides import apply_overrides, parse_overrides, parse_value
from rlab.config.resolver import resolve_string, resolve_values
from rlab.errors import ConfigError, ReferenceError
from rlab.references.parser import parse_reference
from rlab.references.refs import ReferenceKind


def test_config_loading_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "lab.toml").write_text(
        "[project]\nname='base'\n[paths]\nruns='${project.root}/custom-runs'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RLAB__PROJECT__NAME", "environment")
    config = load_config(tmp_path, ("project.name=cli",))
    assert config.project.name == "cli"
    assert config.paths.runs == tmp_path / "custom-runs"


def test_overrides_and_reference_resolution(tmp_path: Path) -> None:
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


def test_invalid_config_and_missing_optional_hydra(tmp_path: Path) -> None:
    (tmp_path / "lab.toml").write_text("[modules]\nload='not-a-list'\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)
    with (
        patch(
            "rlab.config.hydra_adapter.importlib.import_module",
            side_effect=ImportError("no module"),
        ),
        pytest.raises(ConfigError, match="Hydra"),
    ):
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
    text: str, kind: ReferenceKind, component_kind: str | None, alias: str | None
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


def test_malformed_toml_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "lab.toml").write_text(
        '[modules]\nload = [\n  "a"\n  "b"\n]\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_project_specific_sections_accepted(tmp_path: Path) -> None:
    (tmp_path / "lab.toml").write_text(
        '[project]\nname = "test"\n\n[babylm_eval]\nrepo = "external/babylm"\n',
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.project.name == "test"
    assert config.section("babylm_eval") == {"repo": "external/babylm"}
    assert config.section("nonexistent") is None


def test_project_specific_section_can_be_typed(tmp_path: Path) -> None:
    class AdapterConfig(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")

        repo: Path

    (tmp_path / "lab.toml").write_text(
        '[project]\nname = "test"\n\n[adapter]\nrepo = "external/tool"\n',
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    section = config.section("adapter", AdapterConfig)
    assert section == AdapterConfig(repo=Path("external/tool"))
