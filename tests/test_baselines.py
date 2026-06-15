from __future__ import annotations

import math

import pytest

from rlab import BaselineEntry, BaselineStore
from rlab.baselines import BaselineStore as ModuleBaselineStore


def test_baselines_are_rust_backed() -> None:
    store = BaselineStore()
    store.add(BaselineEntry("smoke", "accuracy", 0.75, "tiny baseline"))

    entries = store.list()

    assert entries[0].name == "smoke"
    assert entries[0].metric == "accuracy"
    assert entries[0].value == 0.75
    assert entries[0].description == "tiny baseline"
    assert ModuleBaselineStore().list() == []


def test_baseline_store_validates_entries_in_rust() -> None:
    store = BaselineStore()

    with pytest.raises(ValueError):
        store.add(BaselineEntry("", "accuracy", 0.75))
    with pytest.raises(ValueError):
        store.add(BaselineEntry("bad", "accuracy", math.inf))
