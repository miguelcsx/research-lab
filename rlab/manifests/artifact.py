from pathlib import Path

from pydantic import Field

from rlab.manifests.base import Manifest


class ArtifactManifest(Manifest):
    artifact_kind: str
    path: Path
    sha256: str
    size_bytes: int
    producer_run: str | None = None
    aliases: tuple[str, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)
