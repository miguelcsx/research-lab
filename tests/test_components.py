from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import rlab
from rlab._runner import _invoke


class ToyParams:
    def __init__(self, width: int, name: str = "toy") -> None:
        if width <= 0:
            raise ValueError("width must be positive")
        self.width = width
        self.name = name

    @classmethod
    def model_validate(cls, value: object) -> "ToyParams":
        if not isinstance(value, dict):
            raise TypeError("ToyParams requires a mapping")
        return cls(width=int(value["width"]), name=str(value.get("name", "toy")))

    @classmethod
    def model_json_schema(cls) -> dict[str, object]:
        return {"type": "object", "properties": {"width": {"type": "integer"}}}


@dataclass(frozen=True)
class DataclassParams:
    width: int
    name: str = "toy"


def _context(tmp_path: Path, params: str) -> rlab.RuntimeContext:
    return rlab.RuntimeContext(
        run_id="run",
        run_dir=tmp_path,
        cache_dir=tmp_path,
        project_root=tmp_path,
        params_json=params,
    )


def test_project_exposes_only_runtime_and_support_decorators(tmp_path: Path) -> None:
    project = rlab.Project("runtime-only-api-test", root=tmp_path)

    for name in (
        "experiment",
        "study",
        "workflow",
        "benchmark",
        "evaluation",
        "adapter",
        "loader",
        "executor",
        "resolver",
        "exporter",
        "reporter",
        "notifier",
    ):
        assert hasattr(project, name)

    for name in (
        "component",
        "build",
        "build_spec",
        "requirements",
        "contract",
        "contracts_for",
        "component_requirements",
        "config",
        "external_evaluation",
        "result_schema",
        "source",
        "transform",
        "filter",
        "group",
        "dedup",
        "sink",
        "check",
        "metric",
        "pipeline",
        "dataset",
        "declare",
        "declaration",
    ):
        assert not hasattr(project, name)


def test_runtime_decorators_register_entries(tmp_path: Path) -> None:
    project = rlab.Project("runtime-entry-test", root=tmp_path)

    @project.experiment("train", params=ToyParams, question="train?")
    def train(ctx: rlab.RuntimeContext) -> dict[str, int]:
        params = ctx.params(ToyParams)
        return {"width": params.width}

    @project.study("study", targets=("experiment:train",), params={"width": 4}, seeds=(1, 2))
    def study(ctx: rlab.RuntimeContext) -> None:
        del ctx

    @project.workflow("flow", steps=({"target": "experiment:train"},))
    def flow(ctx: rlab.RuntimeContext) -> dict[str, bool]:
        del ctx
        return {"ok": True}

    @project.benchmark("bench", target="experiment:train")
    def bench(ctx: rlab.RuntimeContext) -> None:
        del ctx

    @project.evaluation("eval", adapter="adapter:local")
    def eval_(ctx: rlab.RuntimeContext) -> None:
        del ctx

    records = {(record["kind"], record["name"]): record for record in project.records}

    assert records[("experiment", "train")]["metadata"]["question"] == "train?"
    assert records[("experiment", "train")]["metadata"]["param_schema"] == (
        ToyParams.model_json_schema()
    )
    assert records[("study", "study")]["metadata"]["targets"] == ["experiment:train"]
    assert records[("workflow", "flow")]["metadata"]["steps"] == [
        {"target": "experiment:train"}
    ]
    assert records[("benchmark", "bench")]["metadata"]["target"] == "experiment:train"
    assert records[("evaluation", "eval")]["metadata"]["adapter"] == "adapter:local"

    assert _invoke(project, "experiment", "train", _context(tmp_path, '{"width": 8}')) == {
        "width": 8
    }


def test_ctx_params_validates_pydantic_style_and_dataclass_params(tmp_path: Path) -> None:
    ctx = _context(tmp_path, '{"width": 8, "name": "wide"}')

    assert ctx.params(ToyParams).width == 8
    assert ctx.params(DataclassParams) == DataclassParams(width=8, name="wide")
    assert ctx.param("width") == 8
    assert ctx.param("missing", "fallback") == "fallback"
    assert ctx.params_dict() == {"width": 8, "name": "wide"}


def test_ctx_params_validation_errors_surface_at_runtime(tmp_path: Path) -> None:
    project = rlab.Project("runtime-params-error-test", root=tmp_path)

    @project.experiment("bad", params=ToyParams)
    def bad(ctx: rlab.RuntimeContext) -> None:
        ctx.params(ToyParams)

    with pytest.raises(ValueError, match="width must be positive"):
        _invoke(project, "experiment", "bad", _context(tmp_path, '{"width": 0}'))


def test_support_decorators_register_support_entries(tmp_path: Path) -> None:
    project = rlab.Project("support-entry-test", root=tmp_path)

    for decorator_name in (
        "adapter",
        "loader",
        "executor",
        "resolver",
        "exporter",
        "reporter",
        "notifier",
    ):
        decorator = getattr(project, decorator_name)

        @decorator(decorator_name)
        def support(ctx: rlab.RuntimeContext) -> None:
            del ctx

    records = {(record["kind"], record["name"]) for record in project.records}

    assert records == {
        ("adapter", "adapter"),
        ("loader", "loader"),
        ("executor", "executor"),
        ("resolver", "resolver"),
        ("exporter", "exporter"),
        ("reporter", "reporter"),
        ("notifier", "notifier"),
    }


def test_top_level_runtime_api_excludes_removed_domain_surface() -> None:
    for name in (
        "Builder",
        "ComponentSpec",
        "Requirements",
        "ComponentContract",
        "MissingRequirements",
        "MissingRequirementsError",
        "collect_requirements",
        "collect_component_requirements",
        "collect_contracts",
        "list_datasets",
        "resolve_dataset",
        "validate_datasets",
        "CheckpointManager",
        "Assumption",
        "Threat",
        "paired_bootstrap",
        "compare_metric_arrays",
    ):
        assert not hasattr(rlab, name)
