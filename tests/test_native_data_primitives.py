from __future__ import annotations

import rlab
import pytest


def test_native_data_components_are_not_public_api() -> None:
    for name in ("NativeTextFilter", "NativeSimhashDedup", "NativeDocumentAssembler"):
        assert not hasattr(rlab, name)
        assert not hasattr(rlab._rlab, name)

    for name in (
        "DataBoundary",
        "DataDecision",
        "TextFilter",
        "FilterRule",
        "SimhashDedup",
        "DocumentAssembler",
        "data_keep",
        "data_update",
        "data_drop",
        "data_boundary",
        "CheckpointManager",
        "CheckpointRecord",
        "RetentionPolicy",
    ):
        assert not hasattr(rlab, name)
        assert not hasattr(rlab._rlab, name)

    with pytest.raises(ModuleNotFoundError):
        __import__("rlab.data")
