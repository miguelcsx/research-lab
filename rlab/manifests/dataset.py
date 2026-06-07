from pathlib import Path

from pydantic import Field

from rlab.manifests.base import Manifest
from rlab.typing import JsonValue


class DatasetOutput(Manifest):
    path: Path
    sha256: str
    size_bytes: int


class DatasetManifest(Manifest):
    inputs: tuple[str, ...] = ()
    pipeline_project: str | None = None
    pipeline_commit: str | None = None
    stages: tuple[str, ...] = ()
    outputs: dict[str, DatasetOutput] = Field(default_factory=dict)
    stats: dict[str, JsonValue] = Field(default_factory=dict)
    checks: dict[str, str] = Field(default_factory=dict)
    licenses: tuple[str, ...] = ()
