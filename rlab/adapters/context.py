from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rlab.context.runtime import RuntimeContext


class AdapterContext(BaseModel):
    """Read-only view passed to every lifecycle method of an ExternalAdapter.

    Adapters never touch global state — they receive everything they need here.
    `inputs` carries adapter-specific parameters resolved by the caller.
    `work_dir` is a per-run sandbox where the adapter may write scratch files.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    runtime: RuntimeContext
    adapter: str
    work_dir: Path
    inputs: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)

    def with_artifacts(self, mapping: dict[str, Path]) -> AdapterContext:
        return self.model_copy(update={"artifacts": {**self.artifacts, **mapping}})

    def project_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the project root."""
        return _resolve_path(path, self.runtime.paths.root)

    def artifact_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the project artifact root."""
        return _resolve_path(path, self.runtime.paths.artifacts)

    def external_output_dir(
        self,
        source: str | Path,
        target: str | Path,
        *,
        migrate: bool = True,
    ) -> Path:
        """Link an external tool output directory to a project artifact directory.

        Many external tools write fixed relative paths under their working
        directory. This helper lets adapters keep those tools unchanged while
        storing the bytes in rlab-managed artifact space.
        """
        source_path = self.project_path(source)
        target_path = self.artifact_path(target)
        link_output_dir(source_path, target_path, migrate=migrate)
        return target_path

    def external_workspace(
        self,
        source: str | Path,
        outputs: Mapping[str | Path, str | Path],
    ) -> Path:
        """Create an immutable external-repo view with artifact-backed outputs."""
        source_path = self.project_path(source)
        workspace = self.work_dir / "external" / source_path.name
        if not workspace.exists():
            workspace.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                source_path,
                workspace,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )

        for relative, target in outputs.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(f"External workspace output must be relative: {relative}")
            target_path = self.artifact_path(target)
            _seed_output(source_path / relative_path, target_path)
            _replace_with_link(workspace / relative_path, target_path)
        return workspace


def link_output_dir(source: Path, target: Path, *, migrate: bool = True) -> None:
    """Make ``source`` point to ``target``, preserving existing contents."""
    target.mkdir(parents=True, exist_ok=True)

    if source.is_symlink():
        if source.resolve() == target.resolve():
            return
        source.unlink()
    elif source.exists():
        if not source.is_dir():
            raise RuntimeError(f"Expected directory or symlink: {source}")
        if migrate:
            _move_children(source, target)
        elif any(source.iterdir()):
            raise RuntimeError(f"Output directory is not empty: {source}")
        source.rmdir()
    else:
        source.parent.mkdir(parents=True, exist_ok=True)

    source.symlink_to(target, target_is_directory=True)


def _resolve_path(path: str | Path, base: Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.absolute()
    return (base / candidate).absolute()


def _move_children(source: Path, target: Path) -> None:
    for child in source.iterdir():
        destination = target / child.name
        if destination.exists():
            raise RuntimeError(
                f"Cannot migrate {child} into {target}; {destination} already exists."
            )
        shutil.move(str(child), str(destination))


def _seed_output(source: Path, target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        return
    target.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)


def _replace_with_link(source: Path, target: Path) -> None:
    if source.is_symlink() or source.is_file():
        source.unlink()
    elif source.exists():
        shutil.rmtree(source)
    source.parent.mkdir(parents=True, exist_ok=True)
    source.symlink_to(target, target_is_directory=True)
