from __future__ import annotations

from pathlib import Path

import pytest

from rlab.adapters.base import BaseAdapter
from rlab.adapters.context import AdapterContext
from rlab.context.runtime import RuntimeContext


def test_base_adapter_noops() -> None:
    adapter = BaseAdapter()
    ctx = object()
    adapter.prepare(ctx)  # type: ignore[arg-type]
    assert adapter.validate_inputs(ctx) == ()  # type: ignore[arg-type]
    assert adapter.collect_outputs(ctx) == {}  # type: ignore[arg-type]
    assert adapter.parse_metrics(ctx) == {}  # type: ignore[arg-type]
    assert adapter.register_artifacts(ctx) == {}  # type: ignore[arg-type]
    adapter.cleanup(ctx)  # type: ignore[arg-type]


def test_base_adapter_command_raises() -> None:
    adapter = BaseAdapter()
    with pytest.raises(NotImplementedError, match=".command()"):
        adapter.command(object())  # type: ignore[arg-type]


def test_adapter_context_resolves_project_and_artifact_paths(
    runtime: RuntimeContext,
) -> None:
    ctx = AdapterContext(runtime=runtime, adapter="example", work_dir=runtime.paths.cache)

    assert ctx.project_path("external/tool") == runtime.paths.root / "external/tool"
    assert ctx.artifact_path("eval/results") == runtime.paths.artifacts / "eval/results"


def test_external_output_dir_links_fixed_tool_output_to_artifacts(
    runtime: RuntimeContext,
) -> None:
    source = runtime.paths.root / "external/tool/results"
    source.mkdir(parents=True)
    (source / "metrics.json").write_text("{}", encoding="utf-8")

    ctx = AdapterContext(runtime=runtime, adapter="example", work_dir=runtime.paths.cache)
    target = ctx.external_output_dir("external/tool/results", "eval/results")

    assert target == runtime.paths.artifacts / "eval/results"
    assert source.is_symlink()
    assert source.resolve() == target
    assert (target / "metrics.json").read_text(encoding="utf-8") == "{}"

    assert ctx.external_output_dir("external/tool/results", "eval/results") == target


def test_external_output_dir_rejects_migration_conflicts(
    runtime: RuntimeContext,
) -> None:
    source = runtime.paths.root / "external/tool/results"
    target = runtime.paths.artifacts / "eval/results"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "metrics.json").write_text("new", encoding="utf-8")
    (target / "metrics.json").write_text("old", encoding="utf-8")

    ctx = AdapterContext(runtime=runtime, adapter="example", work_dir=runtime.paths.cache)

    with pytest.raises(RuntimeError, match="already exists"):
        ctx.external_output_dir(Path("external/tool/results"), Path("eval/results"))


def test_base_adapter_prepares_declared_external_output_dirs(
    runtime: RuntimeContext,
) -> None:
    class Adapter(BaseAdapter):
        def external_output_dirs(
            self, ctx: AdapterContext
        ) -> dict[str | Path, str | Path]:
            del ctx
            return {"external/tool/results": "eval/results"}

    ctx = AdapterContext(runtime=runtime, adapter="example", work_dir=runtime.paths.cache)
    Adapter().prepare(ctx)

    source = runtime.paths.root / "external/tool/results"
    assert source.is_symlink()
    assert source.resolve() == runtime.paths.artifacts / "eval/results"


def test_external_workspace_keeps_source_immutable_and_redirects_outputs(
    runtime: RuntimeContext,
) -> None:
    source = runtime.paths.root / "external/tool"
    (source / "scripts").mkdir(parents=True)
    (source / "results").mkdir()
    (source / "scripts/run.py").write_text("print('ok')", encoding="utf-8")
    (source / "results/baseline.json").write_text("{}", encoding="utf-8")

    ctx = AdapterContext(
        runtime=runtime,
        adapter="example",
        work_dir=runtime.paths.cache / "adapters/example",
    )
    workspace = ctx.external_workspace(
        "external/tool",
        {"results": "eval/results"},
    )

    assert not (workspace / "scripts/run.py").is_symlink()
    assert (workspace / "results").is_symlink()
    assert (workspace / "results/baseline.json").read_text(encoding="utf-8") == "{}"

    (workspace / "results/new.json").write_text('{"score": 1}', encoding="utf-8")

    assert not (source / "results/new.json").exists()
    assert (runtime.paths.artifacts / "eval/results/new.json").exists()
