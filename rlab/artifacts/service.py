from __future__ import annotations

from pathlib import Path

from rlab.artifacts.store import ArtifactStore
from rlab.context.runtime import RuntimeContext


def local_store(runtime: RuntimeContext) -> ArtifactStore:
    return ArtifactStore(runtime.paths.artifacts)


def promote_path(  # noqa: PLR0913
    runtime: RuntimeContext,
    source: Path,
    *,
    artifact_kind: str,
    name: str,
    version: str,
    alias: str | None = None,
) -> Path:
    manifest = local_store(runtime).put(artifact_kind, name, version, Path(source), alias=alias)
    return manifest.path
