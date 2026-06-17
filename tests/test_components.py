from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import rlab
from rlab._runner import _invoke_dataset


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


def test_project_builds_component_specs_with_inline_params(tmp_path: Path) -> None:
    project = rlab.Project("component-build-spec-test", root=tmp_path)

    @project.component("transform:scale")
    def scale(*, factor: float) -> float:
        return factor

    assert project.build_spec({"ref": "transform:scale", "factor": 2.5}) == 2.5
    assert project.build_spec({"ref": "scale", "factor": 3.0}, kind="transform") == 3.0


def test_project_ref_builds_component_spec(tmp_path: Path) -> None:
    project = rlab.Project("component-ref-test", root=tmp_path)

    assert project.ref("optimizer:adamw", learning_rate=0.001).to_dict() == {
        "ref": "optimizer:adamw",
        "params": {"learning_rate": 0.001},
    }


def test_project_builds_positional_or_keyword_component_params(tmp_path: Path) -> None:
    project = rlab.Project("component-build-dataclass-test", root=tmp_path)

    @project.component("source:constant")
    class ConstantSource:
        def __init__(self, value: str = "default") -> None:
            self.value = value

    built = cast(
        ConstantSource,
        project.build_spec({"ref": "source:constant", "value": "configured"}),
    )

    assert built.value == "configured"


def test_declared_dataset_executes_component_specs(tmp_path: Path) -> None:
    project = rlab.Project("dataset-spec-execution-test", root=tmp_path)

    @project.source("items")
    class Items:
        def __init__(self, value: str = "x") -> None:
            self.value = value

        def read(self, _ctx: object) -> list[dict[str, str]]:
            return [{"text": self.value}]

    @project.transform("suffix")
    class Suffix:
        def __init__(self, suffix: str = "!") -> None:
            self.suffix = suffix

        def apply(self, record: dict[str, str], _ctx: object) -> dict[str, str]:
            return {"text": record["text"] + self.suffix}

    @project.sink("capture")
    class Capture:
        def __init__(self, label: str = "out") -> None:
            self.label = label

        def write(self, records: list[dict[str, str]], _ctx: object) -> rlab.SinkResult:
            assert records == [{"text": "configured?"}]
            return rlab.SinkResult(self.label, "memory", len(records))

    project.pipeline("pipe", {"ref": "transform:suffix", "suffix": "?"})
    project.dataset(
        "configured",
        source={"ref": "source:items", "value": "configured"},
        pipeline="pipeline:pipe",
        sinks=({"ref": "sink:capture", "label": "captured"},),
    )
    ctx = rlab.RuntimeContext(
        run_id="dataset-spec",
        run_dir=tmp_path,
        cache_dir=tmp_path / "cache",
        project_root=tmp_path,
        params_json="{}",
        seed=None,
    )

    result = _invoke_dataset(project, "configured", ctx)

    assert result["records"] == 1
    assert result["sinks"] == [{"name": "captured", "path": "memory", "records": 1}]


def test_declared_dataset_accepts_component_spec_objects(tmp_path: Path) -> None:
    project = rlab.Project("dataset-component-spec-test", root=tmp_path)

    @project.source("items")
    class Items:
        def __init__(self, value: str = "x") -> None:
            self.value = value

        def read(self, _ctx: object) -> list[dict[str, str]]:
            return [{"text": self.value}]

    @project.sink("capture")
    class Capture:
        def write(self, records: list[dict[str, str]], _ctx: object) -> rlab.SinkResult:
            assert records == [{"text": "configured"}]
            return rlab.SinkResult("captured", "memory", len(records))

    project.dataset(
        "configured",
        source=project.ref("source:items", value="configured"),
        pipeline="pipeline:empty",
        sinks=(project.ref("sink:capture"),),
    )
    project.pipeline("empty")
    ctx = rlab.RuntimeContext(
        run_id="dataset-spec",
        run_dir=tmp_path,
        cache_dir=tmp_path / "cache",
        project_root=tmp_path,
        params_json="{}",
        seed=None,
    )

    result = _invoke_dataset(project, "configured", ctx)

    assert result["records"] == 1
    assert result["sinks"] == [{"name": "captured", "path": "memory", "records": 1}]


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


def test_project_collects_component_requirements(tmp_path: Path) -> None:
    project = rlab.Project("component-requirements-test", root=tmp_path)

    @project.component(
        "objective:clm",
        requires=rlab.Requirements(model_outputs=("lm",), model_heads=("lm",)),
    )
    def clm() -> object:
        return object()

    @project.component(
        "objective:mlm",
        requires=rlab.Requirements(model_outputs=("lm",), batch_fields=("labels",)),
    )
    def mlm() -> object:
        return object()

    requirements = project.component_requirements(
        "objective", (project.ref("objective:clm"), "mlm")
    )

    assert requirements.model_outputs == ("lm",)
    assert requirements.model_heads == ("lm",)
    assert requirements.batch_fields == ("labels",)


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
