from pathlib import Path

from pydantic import Field

from rlab.manifests.base import Manifest
from rlab.typing import JsonValue


class DatasetOutput(Manifest):
    path: Path
    sha256: str
    size_bytes: int
    is_directory: bool = False


class DatasetAudit(Manifest):
    summary: Path
    drop_reasons: Path
    stage_summary: Path
    source_summary: Path
    decisions: Path | None = None
    samples: dict[str, Path] = Field(default_factory=dict)


class DatasetManifest(Manifest):
    inputs: tuple[str, ...] = ()
    declaration: str
    pipeline: str
    components: tuple[str, ...] = ()
    configuration: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
    pipeline_project: str | None = None
    pipeline_commit: str | None = None
    stages: tuple[str, ...] = ()
    outputs: dict[str, DatasetOutput] = Field(default_factory=dict)
    stats: dict[str, JsonValue] = Field(default_factory=dict)
    checks: dict[str, str] = Field(default_factory=dict)
    licenses: tuple[str, ...] = ()
    audit: DatasetAudit
