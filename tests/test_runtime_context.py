from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from rlab import RuntimeContext
from rlab.external import AdapterContext, ExternalPath, ExternalWorkspace


def _context(tmp_path: Path, params: dict[str, object]) -> RuntimeContext:
    return RuntimeContext(
        run_id="run",
        run_dir=tmp_path / "run",
        cache_dir=tmp_path / "cache",
        project_root=tmp_path,
        params_json=__import__("json").dumps(params),
    )


def test_runtime_context_reads_numeric_and_optional_params(tmp_path: Path) -> None:
    ctx = _context(
        tmp_path,
        {"count": 3, "ratio": 0.25, "missing": None, "path": "data/input.txt"},
    )

    assert ctx.int_param("count") == 3
    assert ctx.optional_int_param("missing") is None
    assert ctx.number_param("count") == 3.0
    assert ctx.number_param("ratio") == 0.25
    assert ctx.path_param("path") == tmp_path / "data/input.txt"


def test_runtime_context_rejects_boolean_numbers(tmp_path: Path) -> None:
    ctx = _context(tmp_path, {"value": True})

    with pytest.raises(TypeError, match="integer"):
        ctx.int_param("value")
    with pytest.raises(TypeError, match="numeric"):
        ctx.number_param("value")


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
