from __future__ import annotations

from pathlib import Path

import pytest

from rlab._protocol import HostRequest
from rlab.runner import RuntimeContext


def _context(tmp_path: Path, params: dict[str, object]) -> RuntimeContext:
    return RuntimeContext(
        HostRequest(
            protocol_version=1,
            request_id="test",
            command="execute",
            project_root=str(tmp_path),
            modules=[],
            target=None,
            run_id="run",
            run_dir=str(tmp_path / "run"),
            cache_dir=str(tmp_path / "cache"),
            params=params,
            seed=None,
            strict=False,
            environment={},
        )
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
