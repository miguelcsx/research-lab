"""Python result and artifact facades backed by Rust-compatible schemas."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from collections.abc import Mapping

from rlab._typing import JsonObject, JsonValue


@dataclass(slots=True)
class FileArtifact:
    """A file artifact produced by a run."""

    name: str
    path: str | Path
    kind: str = "file"
    version: str = "1"
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def to_event_payload(self) -> JsonObject:
        """Return the protocol payload used by the Python runner."""
        return {
            "schema_version": 1,
            "kind": self.kind,
            "name": self.name,
            "path": str(self.path),
            "version": self.version,
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        """Serialize the artifact as stable JSON."""
        return json.dumps(self.to_event_payload(), sort_keys=True)


@dataclass(slots=True)
class FigureArtifact(FileArtifact):
    """A figure artifact."""

    kind: str = "figure"


@dataclass(slots=True)
class TableArtifact(FileArtifact):
    """A table artifact."""

    kind: str = "table"


@dataclass(slots=True)
class LogArtifact(FileArtifact):
    """A log artifact."""

    kind: str = "log"


@dataclass(slots=True)
class ResultSchema:
    """Declarative result schema descriptor."""

    name: str
    fields: Mapping[str, str] = field(default_factory=dict)
    version: str = "1"

    def to_dict(self) -> JsonObject:
        """Return a JSON-serializable schema description."""
        return asdict(self)
