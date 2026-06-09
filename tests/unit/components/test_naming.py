from __future__ import annotations

from rlab.components import display_name


class _Named:
    name = "team.solver"


class _HuggingFaceStyle:
    name_or_path = "org/model"


class _Anonymous:
    pass


def test_display_name_resolves_reference_strings() -> None:
    assert display_name("model:project.constant") == "project.constant"
    assert display_name("hf:org/model") == "org/model"
    assert display_name("plain-string") == "plain-string"


def test_display_name_probes_object_attributes() -> None:
    assert display_name(_Named()) == "team.solver"
    assert display_name(_Anonymous()) == ""
    assert display_name(_Anonymous(), default="fallback") == "fallback"


def test_display_name_supports_custom_attributes() -> None:
    target = _HuggingFaceStyle()
    assert display_name(target) == ""
    assert display_name(target, attributes=("name_or_path", "name")) == "org/model"
