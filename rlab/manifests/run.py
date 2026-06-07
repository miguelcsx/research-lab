from datetime import datetime

from pydantic import Field

from rlab.constants import RunStatus
from rlab.manifests.base import Manifest
from rlab.typing import JsonValue


class RunManifest(Manifest):
    operation: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    command: tuple[str, ...] = ()
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()
    notes: str | None = None
    error: str | None = None
    parent_run: str | None = None
