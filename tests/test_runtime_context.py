from __future__ import annotations

from pathlib import Path
from typing import cast

import json
import pytest

from rlab import RuntimeContext
from rlab.external import AdapterContext, ExternalPath, ExternalWorkspace


class RuntimeConfig:
    def __init__(self, width: int) -> None:
        self.width = width

    @classmethod
    def model_validate(cls, value: object) -> "RuntimeConfig":
        if isinstance(value, RuntimeConfig):
            return value
        if not isinstance(value, dict):
            raise TypeError("RuntimeConfig requires a mapping")
        return cls(width=int(value["width"]))

    def model_dump(self) -> dict[str, int]:
        return {"width": self.width}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RuntimeConfig) and self.width == other.width


def _context(tmp_path: Path, params: dict[str, object]) -> RuntimeContext:
    run_dir = tmp_path / ".rlab" / "runs" / "run"
    cache_dir = tmp_path / ".rlab" / "cache"
    run_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return RuntimeContext(
        run_id="run",
        run_dir=run_dir,
        cache_dir=cache_dir,
        project_root=tmp_path,
        params_json=json.dumps(params),
    )


def test_runtime_context_reads_numeric_and_optional_params(tmp_path: Path) -> None:
    ctx = _context(
        tmp_path,
        {
            "count": 3,
            "ratio": 0.25,
            "enabled": True,
            "missing": None,
            "path": "data/input.txt",
        },
    )

    assert ctx.int_param("count") == 3
    assert ctx.optional_int_param("missing") is None
    assert ctx.number_param("count") == 3.0
    assert ctx.number_param("ratio") == 0.25
    assert ctx.bool_param("enabled") is True
    assert ctx.bool_param("absent", False) is False
    assert ctx.path_param("path") == tmp_path / "data/input.txt"


def test_runtime_context_rejects_boolean_numbers(tmp_path: Path) -> None:
    ctx = _context(tmp_path, {"value": True})

    with pytest.raises(TypeError, match="integer"):
        ctx.int_param("value")
    with pytest.raises(TypeError, match="numeric"):
        ctx.number_param("value")


def test_runtime_context_rejects_non_boolean_bool_param(tmp_path: Path) -> None:
    ctx = _context(tmp_path, {"value": "true"})

    with pytest.raises(TypeError, match="boolean"):
        ctx.bool_param("value")


def test_runtime_context_overrides_prefixes_non_shell_params(tmp_path: Path) -> None:
    ctx = _context(
        tmp_path,
        {"config": "smoke", "runtime.max_words_seen": 20, "data.train_path": "train"},
    )

    assert ctx.overrides(
        exclude=("config",),
        path_prefix="trainer.params",
        passthrough_roots=("data",),
    ) == {
        "trainer.params.runtime.max_words_seen": 20,
        "data.train_path": "train",
    }


def test_runtime_context_manifest_and_artifact_helpers(tmp_path: Path) -> None:
    ctx = _context(tmp_path, {})
    manifest = ctx.write_manifest(
        "manifest.json",
        {"schema_version": 1},
        artifact="run.manifest",
    )
    directory = ctx.output_path(Path("dir"))
    directory.mkdir()
    file_path = directory / "value.txt"
    file_path.write_text("ok", encoding="utf-8")

    assert json.loads(manifest.read_text(encoding="utf-8")) == {"schema_version": 1}
    assert ctx.save_file("value", file_path) == file_path
    assert ctx.save_dir("dir", directory) == directory


def test_runtime_context_config_applies_overrides_and_validates(tmp_path: Path) -> None:
    ctx = _context(tmp_path, {"width": 16})

    config = cast(
        RuntimeConfig,
        ctx.config(RuntimeConfig, RuntimeConfig(width=8)),
    )

    assert config == RuntimeConfig(width=16)


def test_runtime_context_run_executes_child_run(tmp_path: Path) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "__init__.py").write_text(
        """
import rlab

lab = rlab.Project()

@lab.workflow("child", step="run")
def child(ctx):
    output = ctx.output_path("artifact.txt")
    output.write_text(ctx.str_param("message"), encoding="utf-8")
    ctx.log_metric("child.score", 0.5)
    ctx.save_file("message", output)
    return {"ok": True}
""",
        encoding="utf-8",
    )
    ctx = _context(tmp_path, {})

    child = ctx.run("workflow:child", {"message": "hello"}, seed=3)

    assert child.status == "completed"
    assert child.metrics()["child.score"] == 0.5
    assert child.artifact("message").read_text(encoding="utf-8") == "hello"
    assert (tmp_path / ".rlab" / "runs" / "run" / "child_runs.jsonl").exists()


def test_external_workspace_preserves_symlinked_directories(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    source.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    (source / "regular").mkdir()
    (source / "regular" / "data.txt").write_text("inside", encoding="utf-8")
    (source / "linked").symlink_to(outside, target_is_directory=True)

    ctx = _context(tmp_path, {"repo": "source"})
    adapter = cast(
        AdapterContext,
        ctx.external_workspace(
            "adapter",
            ExternalWorkspace(
                "repo",
                "source",
                outputs=(ExternalPath("results", "results"),),
            ),
        ),
    )

    assert (adapter.workspace / "regular" / "data.txt").read_text(
        encoding="utf-8"
    ) == "inside"
    assert (adapter.workspace / "linked").is_symlink()
    assert (adapter.workspace / "linked").resolve() == outside
    assert (adapter.workspace / "results").is_symlink()
    assert (adapter.outputs / "results").is_dir()
