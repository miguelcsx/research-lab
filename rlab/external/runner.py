import contextlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Protocol, TypeAlias, cast

from pydantic import BaseModel, ConfigDict

from rlab.errors import ExternalRunError
from rlab.external.command import ExternalCommand
from rlab.external.sandbox import safe_workdir, sandbox_environment

_MAX_OUTPUT_BYTES = 10 * 1024 * 1024
_TRUNCATED_MARKER = "\n... [output truncated]"
_READ_CHUNK_BYTES = 4096
_PTY_DRAIN_SECONDS = 2.0
_PTY_CLOSE_JOIN_SECONDS = 1.0
_POLL_INTERVAL_SECONDS = 0.05

CommandArgs: TypeAlias = tuple[str, ...]
Environment: TypeAlias = dict[str, str]
RunOutput: TypeAlias = tuple[int, str, str]
RunnerFn: TypeAlias = Callable[[CommandArgs, Path, Environment, int | None], RunOutput]

_HAS_PTY = (
    importlib.util.find_spec("pty") is not None
    and importlib.util.find_spec("termios") is not None
)

if _HAS_PTY:
    import fcntl as _fcntl
    import pty as _pty
    import struct as _struct
    import termios as _termios


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    returncode: int
    stdout: str
    stderr: str
    command: tuple[str, ...]
    artifacts: tuple[Path, ...] = ()


class ExternalRunner(Protocol):
    def run(self, command: ExternalCommand, root: Path) -> CommandResult: ...


@dataclass(slots=True)
class _BoundedBuffer:
    limit: int
    _data: bytearray
    _seen: int = 0

    @classmethod
    def create(cls, limit: int = _MAX_OUTPUT_BYTES) -> "_BoundedBuffer":
        return cls(limit=limit, _data=bytearray())

    def append(self, chunk: bytes) -> None:
        available = max(self.limit - len(self._data), 0)
        self._data.extend(chunk[:available])
        self._seen += len(chunk)

    def text(self) -> str:
        value = bytes(self._data).decode("utf-8", errors="replace")
        return f"{value}{_TRUNCATED_MARKER}" if self.truncated else value

    @property
    def truncated(self) -> bool:
        return self._seen > self.limit


@dataclass(frozen=True, slots=True)
class _ProcessOutput:
    returncode: int
    stdout: str
    stderr: str

    def as_tuple(self) -> RunOutput:
        return self.returncode, self.stdout, self.stderr


def _decode_limited(data: bytes) -> str:
    buffer = _BoundedBuffer.create()
    buffer.append(data)
    return buffer.text()


def _stream_bytes(sink: IO[str], data: bytes) -> None:
    binary_sink = getattr(sink, "buffer", None)

    if binary_sink is not None:
        binary_sink.write(data)
        binary_sink.flush()
        return

    sink.write(data.decode("utf-8", errors="replace"))
    sink.flush()


def _capture_limited(
    args: CommandArgs,
    cwd: Path,
    env: Environment,
    timeout: int | None,
) -> RunOutput:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )

    return _ProcessOutput(
        returncode=completed.returncode,
        stdout=_decode_limited(completed.stdout),
        stderr=_decode_limited(completed.stderr),
    ).as_tuple()


def _deadline(timeout: int | None) -> float | None:
    return None if timeout is None else time.monotonic() + timeout


def _timed_out(deadline: float | None) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.kill()
    process.wait()


def _wait_without_exceptions(
    process: subprocess.Popen[bytes],
    timeout: int | None,
) -> int:
    deadline = _deadline(timeout)

    while process.poll() is None:
        if _timed_out(deadline):
            _terminate_process(process)
            raise subprocess.TimeoutExpired(process.args, timeout)

        time.sleep(_POLL_INTERVAL_SECONDS)

    return int(process.returncode)


def _join_all(
    threads: Iterable[threading.Thread], timeout: float | None = None
) -> None:
    for thread in threads:
        thread.join(timeout=timeout)


def _read_stream(
    source: IO[bytes],
    sink: IO[str],
    capture: _BoundedBuffer,
) -> None:
    for chunk in iter(lambda: source.read(_READ_CHUNK_BYTES), b""):
        capture.append(chunk)
        _stream_bytes(sink, chunk)


def _stream_pipes(
    args: CommandArgs,
    cwd: Path,
    env: Environment,
    timeout: int | None,
) -> RunOutput:
    process = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = _BoundedBuffer.create()
    stderr = _BoundedBuffer.create()

    stdout_pipe = cast(IO[bytes], process.stdout)
    stderr_pipe = cast(IO[bytes], process.stderr)

    threads = (
        threading.Thread(
            target=_read_stream,
            args=(stdout_pipe, sys.stdout, stdout),
            daemon=True,
        ),
        threading.Thread(
            target=_read_stream,
            args=(stderr_pipe, sys.stderr, stderr),
            daemon=True,
        ),
    )

    for thread in threads:
        thread.start()

    returncode = _wait_without_exceptions(process, timeout)
    _join_all(threads)

    return _ProcessOutput(
        returncode=returncode,
        stdout=stdout.text(),
        stderr=stderr.text(),
    ).as_tuple()


def _disable_pty_output_processing(fd: int) -> None:
    attrs = _termios.tcgetattr(fd)
    attrs[1] &= ~_termios.OPOST
    _termios.tcsetattr(fd, _termios.TCSANOW, attrs)


def _set_pty_window(fd: int, rows: int = 24, cols: int = 80) -> None:
    window_size = _struct.pack("HHHH", rows, cols, 0, 0)
    _fcntl.ioctl(fd, _termios.TIOCSWINSZ, window_size)


def _configure_pty_slaves(fds: Sequence[int]) -> None:
    for fd in fds:
        _disable_pty_output_processing(fd)
        _set_pty_window(fd)


def _close_fds(fds: Iterable[int]) -> None:
    for fd in fds:
        with contextlib.suppress(OSError):
            os.close(fd)


def _read_pty(
    master_fd: int,
    sink: IO[str],
    capture: _BoundedBuffer,
) -> None:
    while True:
        with contextlib.suppress(OSError):
            data = os.read(master_fd, _READ_CHUNK_BYTES)
            if data:
                capture.append(data)
                _stream_bytes(sink, data)
                continue
        break


def _stream_pty(
    args: CommandArgs,
    cwd: Path,
    env: Environment,
    timeout: int | None,
) -> RunOutput:
    master_out, slave_out = _pty.openpty()
    master_err, slave_err = _pty.openpty()

    slave_fds = (slave_out, slave_err)
    master_fds = (master_out, master_err)

    _configure_pty_slaves(slave_fds)

    process = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=slave_out,
        stderr=slave_err,
        close_fds=True,
    )

    _close_fds(slave_fds)

    stdout = _BoundedBuffer.create()
    stderr = _BoundedBuffer.create()

    threads = (
        threading.Thread(
            target=_read_pty,
            args=(master_out, sys.stdout, stdout),
            daemon=True,
        ),
        threading.Thread(
            target=_read_pty,
            args=(master_err, sys.stderr, stderr),
            daemon=True,
        ),
    )

    for thread in threads:
        thread.start()

    returncode = _wait_without_exceptions(process, timeout)

    _join_all(threads, timeout=_PTY_DRAIN_SECONDS)
    _close_fds(master_fds)
    _join_all(threads, timeout=_PTY_CLOSE_JOIN_SECONDS)

    return _ProcessOutput(
        returncode=returncode,
        stdout=stdout.text(),
        stderr=stderr.text(),
    ).as_tuple()


def _has_terminal_streams() -> bool:
    return sys.stdout.isatty() and sys.stderr.isatty()


def _stream_runner() -> RunnerFn:
    return _stream_pty if _HAS_PTY and _has_terminal_streams() else _stream_pipes


def _stream_and_capture(
    args: CommandArgs,
    cwd: Path,
    env: Environment,
    timeout: int | None,
) -> RunOutput:
    return _stream_runner()(args, cwd, env, timeout)


def _runner_for(command: ExternalCommand) -> RunnerFn:
    return _stream_and_capture if command.stream else _capture_limited


def _build_result(command: ExternalCommand, output: RunOutput) -> CommandResult:
    returncode, stdout, stderr = output

    return CommandResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        command=command.args,
    )


def _raise_on_failure(result: CommandResult) -> None:
    if result.returncode == 0:
        return

    message = result.stderr.strip() or result.stdout.strip()
    raise ExternalRunError(f"External command failed ({result.returncode}): {message}")


def _env_or_empty(env: dict[str, str] | None) -> dict[str, str]:
    return {} if env is None else env


class ShellRunner:
    def run(self, command: ExternalCommand, root: Path) -> CommandResult:
        output = _runner_for(command)(
            command.args,
            cwd=safe_workdir(root, command.cwd),
            env=sandbox_environment(command.env),
            timeout=command.timeout_seconds,
        )

        result = _build_result(command, output)
        _raise_on_failure(result)
        return result


class PythonModuleRunner(ShellRunner):
    def command(
        self,
        module: str,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExternalCommand:
        return ExternalCommand(
            args=("python", "-m", module, *args),
            cwd=cwd,
            env=_env_or_empty(env),
            timeout_seconds=timeout_seconds,
        )


class UvRunner(ShellRunner):
    def command(
        self,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExternalCommand:
        return ExternalCommand(
            args=("uv", "run", *args),
            cwd=cwd,
            env=_env_or_empty(env),
            timeout_seconds=timeout_seconds,
        )


class CondaRunner(ShellRunner):
    def command(
        self,
        environment: str,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExternalCommand:
        return ExternalCommand(
            args=("conda", "run", "-n", environment, *args),
            cwd=cwd,
            env=_env_or_empty(env),
            timeout_seconds=timeout_seconds,
        )


class DockerRunner(ShellRunner):
    def command(
        self,
        image: str,
        *args: str,
        mounts: tuple[tuple[Path, str], ...] = (),
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExternalCommand:
        mount_args = tuple(
            item
            for source, target in mounts
            for item in ("-v", f"{source.resolve()}:{target}")
        )

        return ExternalCommand(
            args=("docker", "run", "--rm", *mount_args, image, *args),
            cwd=cwd,
            env=_env_or_empty(env),
            timeout_seconds=timeout_seconds,
        )
