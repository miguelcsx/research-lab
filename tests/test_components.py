from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
import rlab
from rlab._runner import _invoke, _invoke_dataset


class ToyConfig:
    def __init__(self, width: int, name: str = "toy") -> None:
        if width <= 0:
            raise ValueError("width must be positive")
        self.width = width
        self.name = name

    @classmethod
    def model_validate(cls, value: object) -> "ToyConfig":
        if isinstance(value, ToyConfig):
            return value
        if not isinstance(value, dict):
            raise TypeError("ToyConfig requires a mapping")
        return cls(width=int(value["width"]), name=str(value.get("name", "toy")))

    @classmethod
    def model_json_schema(cls) -> dict[str, object]:
        return {"type": "object", "properties": {"width": {"type": "integer"}}}

    def model_dump(self, mode: str = "python") -> dict[str, object]:
        del mode
        return {"width": self.width, "name": self.name}

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ToyConfig)
            and self.width == other.width
            and self.name == other.name
        )


@dataclass(frozen=True, slots=True)
class ScaleSpec:
    factor: float


def test_typed_component_specs_are_registered_and_built(tmp_path: Path) -> None:
    project = rlab.Project("typed-component-test", root=tmp_path)

    @project.component("transform:scale", spec=ScaleSpec)
    def scale(prefix: str, spec: ScaleSpec) -> tuple[str, float]:
        return prefix, spec.factor

    spec = ScaleSpec(2.5)

    assert rlab.Builder(project).spec(spec) == {
        "ref": "transform:scale",
        "params": {"factor": 2.5},
    }
    assert rlab.Builder(project)(spec, "value") == ("value", 2.5)


def test_public_project_has_no_spec_factory(tmp_path: Path) -> None:
    assert not hasattr(rlab.Project("no-spec-factory-test", root=tmp_path), "spec")


def test_project_config_applies_typed_overrides(tmp_path: Path) -> None:
    project = rlab.Project("config-factory-test", root=tmp_path)

    @project.config("toy:small", schema=ToyConfig)
    def small() -> ToyConfig:
        return ToyConfig(width=8)

    config = project.config("toy:small", overrides={"width": 16})

    assert config == ToyConfig(width=16)
    record = project.record("config", "toy:small")
    assert record["metadata"]["config_reference"] == "toy:small"


def test_project_experiment_declares_typed_params(tmp_path: Path) -> None:
    project = rlab.Project("experiment-params-test", root=tmp_path)

    @project.experiment(
        "configured",
        params=ToyConfig(width=8),
        params_schema=ToyConfig,
    )
    def configured(ctx: rlab.RuntimeContext, config: ToyConfig) -> dict[str, int]:
        del ctx
        return {"width": config.width}

    record = project.record("experiment", "configured")
    assert record["metadata"]["params"] == {"width": 8, "name": "toy"}
    assert record["metadata"]["params_schema"] == ToyConfig.model_json_schema()

    ctx = rlab.RuntimeContext(
        run_id="run",
        run_dir=tmp_path,
        cache_dir=tmp_path,
        project_root=tmp_path,
        params_json='{"data.path": "train", "width": 16}',
    )

    assert _invoke(project, "experiment", "configured", ctx) == {"width": 16}


def test_experiment_spec_serializes_params() -> None:
    from rlab.experiments import Experiment

    assert Experiment(
        name="configured",
        params={"runtime.max_words_seen": 20},
    ).to_dict()["params"] == {"runtime.max_words_seen": 20}


def test_project_experiment_validates_params_without_injection(tmp_path: Path) -> None:
    project = rlab.Project("experiment-params-validation-test", root=tmp_path)

    @project.experiment(
        "configured",
        params=ToyConfig(width=8),
        params_schema=ToyConfig,
    )
    def configured(ctx: rlab.RuntimeContext) -> dict[str, bool]:
        del ctx
        return {"ok": True}

    ctx = rlab.RuntimeContext(
        run_id="run",
        run_dir=tmp_path,
        cache_dir=tmp_path,
        project_root=tmp_path,
        params_json='{"width": 0}',
    )

    with pytest.raises(ValueError, match="width must be positive"):
        _invoke(project, "experiment", "configured", ctx)


def test_empty_experiment_params_validates_runtime_config(tmp_path: Path) -> None:
    project = rlab.Project("study-owned-params-test", root=tmp_path)

    @project.experiment("configured", params_schema=ToyConfig)
    def configured(ctx: rlab.RuntimeContext, config: ToyConfig) -> dict[str, int]:
        del ctx
        return {"width": config.width}

    ctx = rlab.RuntimeContext(
        run_id="run",
        run_dir=tmp_path,
        cache_dir=tmp_path,
        project_root=tmp_path,
        params_json='{"data.path": "train", "seed": 7, "width": 16}',
        seed=7,
    )

    assert _invoke(project, "experiment", "configured", ctx) == {"width": 16}


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
        source={"ref": "source:items", "value": "configured"},
        pipeline="pipeline:empty",
        sinks=({"ref": "sink:capture"},),
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


def test_project_includes_data_builtins_out_of_the_box(tmp_path: Path) -> None:
    project = rlab.Project("builtin-data-test", root=tmp_path)
    records = {f"{record['kind']}:{record['name']}": record for record in project.records}

    assert "filter:rlab.text" in records
    assert "dedup:rlab.simhash" in records
    assert "group:rlab.documents" in records
    for reference in ("filter:rlab.text", "dedup:rlab.simhash", "group:rlab.documents"):
        metadata = records[reference]["metadata"]
        assert isinstance(metadata, dict)
        assert metadata["builtin"] is True
        assert metadata["params_schema"]["type"] == "object"


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
        "objective", ("clm", "mlm")
    )

    assert requirements.model_outputs == ("lm",)
    assert requirements.model_heads == ("lm",)
    assert requirements.batch_fields == ("labels",)


def test_component_contracts_include_provides_and_aggregate_specs(tmp_path: Path) -> None:
    project = rlab.Project("component-contract-test", root=tmp_path)

    @project.component(
        "objective:lm",
        requires=rlab.Requirements(model_heads=("lm",), batch_fields=("labels",)),
    )
    def lm() -> None:
        return None

    @project.component(
        "model:toy",
        provides=rlab.Requirements(model_heads=("lm",), capabilities=("causal",)),
    )
    def toy() -> None:
        return None

    objective_contract = project.contract("objective", "lm")
    model_contract = project.contract("model", "toy")

    assert objective_contract.requires.model_heads == ("lm",)
    assert model_contract.provides.capabilities == ("causal",)
    assert project.requirements_for("objective", ["lm"]) == (
        rlab.Requirements(model_heads=("lm",), batch_fields=("labels",))
    )
    assert project.contracts_for("model", ["toy"]).provides == rlab.Requirements(
        model_heads=("lm",), capabilities=("causal",)
    )


def test_missing_requirements_reports_each_field() -> None:
    missing = rlab.missing_requirements(
        rlab.Requirements(
            model_outputs=("hidden",),
            model_heads=("lm",),
            batch_fields=("labels",),
            capabilities=("causal",),
            artifacts=("tokenizer",),
        ),
        rlab.Requirements(model_heads=("lm",)),
    )

    assert not missing.ok
    assert missing.model_outputs == ("hidden",)
    assert missing.model_heads == ()
    assert missing.batch_fields == ("labels",)
    assert missing.capabilities == ("causal",)
    assert missing.artifacts == ("tokenizer",)
    assert rlab.missing_requirements(
        rlab.Requirements(batch_fields=("labels",), model_heads=("lm",)),
        rlab.Requirements(),
        fields=("batch_fields",),
    ).to_dict() == {
        "model_outputs": [],
        "model_heads": [],
        "batch_fields": ["labels"],
        "capabilities": [],
        "artifacts": [],
    }
    assert rlab.Requirements(model_heads=("lm",), batch_fields=("labels",)).only(
        "model_heads"
    ) == rlab.Requirements(model_heads=("lm",))
    with pytest.raises(rlab.MissingRequirementsError, match="test contract"):
        missing.raise_if_any("test contract")


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
