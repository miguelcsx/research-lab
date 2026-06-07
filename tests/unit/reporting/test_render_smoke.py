from __future__ import annotations

import importlib
from pathlib import Path

from rlab.artifacts.layout import metadata_path, object_path
from rlab.cache.paths import CachePaths
from rlab.cli.render.console import console
from rlab.cli.render.errors import render_error
from rlab.cli.render.panels import result_panel
from rlab.cli.render.progress import progress


def test_public_declaration_modules_import_and_render_helpers(tmp_path: Path) -> None:
    for module in (
        "rlab.cli.options",
        "rlab.data.metric",
        "rlab.data.source",
        "rlab.data.transform",
        "rlab.launchers.base",
    ):
        assert importlib.import_module(module)

    assert object_path(tmp_path, "abcdef") == tmp_path / "objects" / "ab" / "cdef"
    assert metadata_path(tmp_path, "model", "tiny").name == "tiny.yaml"
    paths = CachePaths(root=tmp_path)
    assert paths.downloads == tmp_path / "downloads"
    assert paths.artifacts == tmp_path / "artifacts"
    assert paths.indexes == tmp_path / "indexes"
    assert result_panel("ok", "done").border_style == "green"
    assert result_panel("bad", "failed", success=False).border_style == "red"
    with progress() as display:
        display.add_task("test", total=1)
    render_error(console, ValueError("expected"))
