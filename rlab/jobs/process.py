from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

_PS_TIMEOUT_SECONDS = 5.0
_CANCEL_WAIT_SECONDS = 0.05
_CANCEL_WAIT_RETRIES = 20


def process_start(pid: int) -> str:
    """Return an opaque identifier for the process start time.

    On Linux uses /proc/<pid>/stat field 21. On other Unix-like systems uses
    ``ps -o lstart= -p PID``. On Windows returns ''.
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
            timeout=_PS_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
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
    """Spawn a subprocess and return the Popen handle.

    Stdout and stderr are redirected to *log*.  The caller should eventually
    call ``wait()`` on the returned handle to avoid zombie processes.
    """
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process


def cancel_process(process: subprocess.Popen[bytes]) -> None:
    """Cancel a running subprocess and wait for it to terminate."""
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=_CANCEL_WAIT_SECONDS * _CANCEL_WAIT_RETRIES)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(process.pid, signal.SIGKILL)
        process.wait()


def cancel_pid(pid: int) -> None:
    """Cancel a running process by PID (legacy sessions without Popen handle)."""
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(pid, signal.SIGTERM)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, signal.SIGTERM)
    for _ in range(_CANCEL_WAIT_RETRIES):
        if not _pid_alive(pid):
            return
        time.sleep(_CANCEL_WAIT_SECONDS)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
