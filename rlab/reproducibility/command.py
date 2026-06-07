import shlex
from collections.abc import Sequence
from pathlib import Path


def write_command(path: Path, command: Sequence[str]) -> None:
    path.write_text(shlex.join(command) + "\n")
