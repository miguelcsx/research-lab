import os
import signal
import subprocess
from pathlib import Path


def process_start(pid: int) -> str:
    stat = Path(f"/proc/{pid}/stat")
    if not stat.exists():
        return ""
    return stat.read_text().split()[21]


def is_same_process(pid: int, expected_start: str) -> bool:
    return bool(expected_start) and process_start(pid) == expected_start


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
    os.killpg(pid, signal.SIGTERM)
