from __future__ import annotations

from pathlib import Path

import pytest
import rlab


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


def test_config_lists_and_validates(tmp_path: Path) -> None:
    (tmp_path / "base.yaml").write_text("value: 3\n", encoding="utf-8")

    assert rlab.list_configs(tmp_path) == ("base",)
    assert rlab.validate_configs(tmp_path) == {}


def test_config_rejects_cycles(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("extends: b\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("extends: a\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cyclic config inheritance"):
        rlab.resolve_config(tmp_path, "a")
