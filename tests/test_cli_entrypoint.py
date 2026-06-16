from __future__ import annotations

import rlab.__main__ as entrypoint
import rlab._rlab as native
from pytest import CaptureFixture, MonkeyPatch


def test_cli_entrypoint_prints_errors_without_traceback(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    def fail() -> int:
        raise ValueError("bad ref")

    monkeypatch.setattr(native, "cli_main", fail)

    assert entrypoint.main() == 1
    captured = capsys.readouterr()
    assert captured.err == "bad ref\n"
