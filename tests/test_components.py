from __future__ import annotations

from pathlib import Path

import pytest
import rlab


def test_project_build_infers_component_params(tmp_path: Path) -> None:
    project = rlab.Project("component-build-test", root=tmp_path)

    @project.component(
        "transform:scale",
        requires=rlab.Requirements(capabilities=("numeric",)),
    )
    def scale(prefix: str, *, factor: float) -> tuple[str, float]:
        return prefix, factor

    built = project.build(
        "transform:scale",
        {"factor": 2.5},
        "value",
    )

    assert built == ("value", 2.5)
    assert project.requirements("transform", "scale") == rlab.Requirements(
        capabilities=("numeric",)
    )
    record = project.record("transform", "scale")
    metadata = record["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["params_schema"] == {
        "type": "object",
        "properties": {"factor": {"type": "number"}},
        "required": ["factor"],
        "additionalProperties": False,
    }
    with pytest.raises(ValueError, match="unknown component params"):
        project.build("transform:scale", {"other": 2.5}, "value")


def test_requirements_merge_without_duplicates() -> None:
    requirements = rlab.collect_requirements(
        [
            rlab.Requirements(model_heads=("lm",), capabilities=("tokens",)),
            rlab.Requirements(model_heads=("lm", "rtd"), batch_fields=("labels",)),
        ]
    )

    assert requirements.model_heads == ("lm", "rtd")
    assert requirements.batch_fields == ("labels",)
    assert requirements.capabilities == ("tokens",)


def test_planned_variants_reuse_experiment_registry() -> None:
    project = rlab.Project("planned-variants")

    @project.sweep("search", matrix={"width": [16, 32]}, seeds=(1, 2))
    def search() -> None:
        return None

    @project.ablation("drop_feature")
    def ablation() -> None:
        return None

    records = {
        str(record["name"]): record
        for record in project.records
        if record.get("kind") == "experiment"
    }
    search_metadata = records["search"]["metadata"]
    ablation_metadata = records["drop_feature"]["metadata"]
    assert isinstance(search_metadata, dict)
    assert isinstance(ablation_metadata, dict)
    assert search_metadata["experiment_type"] == "sweep"
    assert ablation_metadata["experiment_type"] == "ablation"
