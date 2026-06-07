from pathlib import Path

import pytest

from rlab.cli.templates import write_project
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return write_project(tmp_path, "project")


@pytest.fixture
def runtime(project: Path) -> RuntimeContext:
    return build_runtime(project)
