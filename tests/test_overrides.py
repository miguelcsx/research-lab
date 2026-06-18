from __future__ import annotations

import pytest
import rlab


def test_apply_overrides_strict_reports_unknown_path() -> None:
    value = {"trainer": {"params": {"width": 8}}}

    assert rlab.apply_overrides(
        value,
        {"trainer.params.width": 16},
        strict=True,
    )["trainer"]["params"]["width"] == 16

    with pytest.raises(Exception, match="trainer.params.depth.value"):
        rlab.apply_overrides(
            value,
            {"trainer.params.depth.value": 2},
            strict=True,
        )
