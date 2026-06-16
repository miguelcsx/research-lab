from __future__ import annotations

from pathlib import Path

import pytest
import rlab


def test_apply_overrides_returns_new_document() -> None:
    document: rlab.JsonObject = {"model": {"width": 32}, "runtime": {"steps": 10}}

    updated = rlab.apply_overrides(document, {"model.width": 64})

    assert updated == {"model": {"width": 64}, "runtime": {"steps": 10}}
    assert document == {"model": {"width": 32}, "runtime": {"steps": 10}}


def test_apply_overrides_rejects_non_mapping_path() -> None:
    with pytest.raises(ValueError, match="crosses non-mapping"):
        rlab.apply_overrides({"model": 32}, {"model.width": 64})


def test_config_extends_and_applies_explicit_overrides(tmp_path: Path) -> None:
    (tmp_path / "base.yaml").write_text(
        "model:\n  width: 32\nruntime:\n  steps: 10\n",
        encoding="utf-8",
    )
    (tmp_path / "child.yaml").write_text(
        "extends: base\nmodel:\n  layers: 2\n",
        encoding="utf-8",
    )

    config = rlab.resolve_config(tmp_path, "child", overrides={"model.width": 64})

    assert config == {
        "model": {"width": 64, "layers": 2},
        "runtime": {"steps": 10},
    }
    with pytest.raises(ValueError, match="explicit dotted path"):
        rlab.resolve_config(tmp_path, "child", overrides={"width": 64})


def test_config_resolves_into_typed_model(tmp_path: Path) -> None:
    class ConfigModel:
        def __init__(self, width: int) -> None:
            self.width = width

        @classmethod
        def model_validate(cls, value: object) -> "ConfigModel":
            assert isinstance(value, dict)
            model = value["model"]
            assert isinstance(model, dict)
            return cls(width=int(model["width"]))

    (tmp_path / "base.yaml").write_text("model:\n  width: 32\n", encoding="utf-8")

    config = rlab.resolve_config(tmp_path, "base", model=ConfigModel)

    assert config.width == 32


def test_config_lists_and_validates(tmp_path: Path) -> None:
    (tmp_path / "base.yaml").write_text("value: 3\n", encoding="utf-8")

    assert rlab.list_configs(tmp_path) == ("base",)
    assert rlab.validate_configs(tmp_path) == {}


def test_config_rejects_cycles(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("extends: b\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("extends: a\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cyclic config inheritance"):
        rlab.resolve_config(tmp_path, "a")
