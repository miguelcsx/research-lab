from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rlab.constants import EntryKind


class RegistryRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    kind: EntryKind
    name: str
    value: Callable[..., Any] | type[Any]
    version: str = "1.0.0"
    target_kind: str | None = None
    module: str
    qualname: str
    source: Path | None = None
    description: str = ""
    tags: tuple[str, ...] = ()
    package: str = "project"
    capabilities: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def namespace(self) -> str:
        return self.name.rpartition(".")[0] or "default"
