import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from rlab.errors import ExternalRunError
from rlab.external.command import ExternalCommand
from rlab.external.sandbox import safe_workdir, sandbox_environment

_MAX_OUTPUT_BYTES = 10 * 1024 * 1024
_TRUNCATED_MARKER = "\n... [output truncated]"


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    returncode: int
    stdout: str
    stderr: str
    command: tuple[str, ...]
    artifacts: tuple[Path, ...] = ()


class ExternalRunner(Protocol):
    def run(self, command: ExternalCommand, root: Path) -> CommandResult: ...


def _capture_limited(
    args: tuple[str, ...],
    cwd: Path,
    env: dict[str, str],
    timeout: int | None,
) -> tuple[int, str, str]:
    with (
        tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stdout_file,
        tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read(_MAX_OUTPUT_BYTES)
        stderr = stderr_file.read(_MAX_OUTPUT_BYTES)
        if len(stdout) >= _MAX_OUTPUT_BYTES:
            stdout = stdout[:_MAX_OUTPUT_BYTES] + _TRUNCATED_MARKER
        if len(stderr) >= _MAX_OUTPUT_BYTES:
            stderr = stderr[:_MAX_OUTPUT_BYTES] + _TRUNCATED_MARKER
        return returncode, stdout, stderr


class ShellRunner:
    def run(self, command: ExternalCommand, root: Path) -> CommandResult:
        returncode, stdout, stderr = _capture_limited(
            command.args,
            cwd=safe_workdir(root, command.cwd),
            env=sandbox_environment(command.env),
            timeout=command.timeout_seconds,
        )
        result = CommandResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            command=command.args,
        )
        if result.returncode:
            raise ExternalRunError(
                f"External command failed ({result.returncode}): {result.stderr.strip()}"
            )
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
            env=env or {},
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
            env=env or {},
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
            env=env or {},
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
            item for source, target in mounts for item in ("-v", f"{source.resolve()}:{target}")
        )
        return ExternalCommand(
            args=("docker", "run", "--rm", *mount_args, image, *args),
            cwd=cwd,
            env=env or {},
            timeout_seconds=timeout_seconds,
        )
