from __future__ import annotations

from pathlib import Path

import pytest
import rlab


def test_read_json_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version": 1, "value": "ok"}\n', encoding="utf-8")

    assert rlab.read_json_manifest(path, required_fields=("schema_version",)) == {
        "schema_version": 1,
        "value": "ok",
    }


def test_read_json_manifest_requires_fields(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version": 1}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="missing required fields"):
        rlab.read_json_manifest(path, required_fields=("missing",))
