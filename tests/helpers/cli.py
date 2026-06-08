from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from rlab.cli.app import app

Command = tuple[str, ...]


def invoke_cli(project: Path, *args: str, runner: CliRunner | None = None) -> Result:
    active_runner = runner or CliRunner()
    return active_runner.invoke(app, ["--root", str(project), *args])


def invoke_json(project: Path, *args: str, runner: CliRunner | None = None) -> Result:
    return invoke_cli(project, "--json", *args, runner=runner)


def assert_success(result: Result, *expected_fragments: str) -> Result:
    if result.exit_code != 0:
        message = result.output
        if result.exception is not None:
            message = f"{message}\nException: {result.exception!r}"
        pytest.fail(message)
    for fragment in expected_fragments:
        assert fragment in result.output
    return result


def assert_failure(result: Result, *expected_fragments: str) -> Result:
    assert result.exit_code != 0
    for fragment in expected_fragments:
        assert fragment in result.output
    return result
