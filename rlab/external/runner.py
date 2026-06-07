import subprocess
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from rlab.errors import ExternalRunError
from rlab.external.command import ExternalCommand
from rlab.external.sandbox import safe_workdir, sandbox_environment


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    returncode: int
    stdout: str
    stderr: str
    command: tuple[str, ...]
    artifacts: tuple[Path, ...] = ()


class ExternalRunner(Protocol):
    def run(self, command: ExternalCommand, root: Path) -> CommandResult: ...


class ShellRunner:
    def run(self, command: ExternalCommand, root: Path) -> CommandResult:
        completed = subprocess.run(
            command.args,
            cwd=safe_workdir(root, command.cwd),
            env=sandbox_environment(command.env),
            text=True,
            capture_output=True,
            timeout=command.timeout_seconds,
            check=False,
        )
        result = CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
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
