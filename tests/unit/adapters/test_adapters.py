from __future__ import annotations

import pytest

from rlab.adapters.base import BaseAdapter


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
