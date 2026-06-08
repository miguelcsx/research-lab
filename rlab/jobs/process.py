from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


def process_start(pid: int) -> str:
    """Return an opaque identifier for the process start time.

    On Linux uses /proc/<pid>/stat field 21. On other Unix-like systems uses
    `ps -o lstart= -p PID`. On Windows returns ''.
    """
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            return stat.read_text().split()[21]
        except (IndexError, OSError):
            return ""
    if sys.platform == "win32":
        return ""
    try:
        result = subprocess.run(
            ("ps", "-o", "lstart=", "-p", str(pid)),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def is_same_process(pid: int, expected_start: str) -> bool:
    if not expected_start:
        return _pid_alive(pid)
    return process_start(pid) == expected_start


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def spawn(command: tuple[str, ...], cwd: Path, log: Path) -> subprocess.Popen[bytes]:
    log.parent.mkdir(parents=True, exist_ok=True)
    stream = log.open("wb")
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=stream,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def cancel(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            os.kill(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
