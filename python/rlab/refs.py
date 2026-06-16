"""Typed references returned by child runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    run_id: str
    name: str
    path: Path
    kind: str
    metadata: Mapping[str, Any]

    def __fspath__(self) -> str:
        return str(self.path)

    def __str__(self) -> str:
        return str(self.path)


@dataclass(frozen=True, slots=True)
class RunRef:
    id: str
    target: str
    path: Path

    def artifact(self, name: str) -> ArtifactRef:
        artifacts = self.path / "artifacts" / "artifacts.jsonl"
        for line in artifacts.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item.get("name") == name:
                path = Path(str(item.get("staged_path") or item["path"]))
                return ArtifactRef(
                    run_id=self.id,
                    name=name,
                    path=path,
                    kind=str(item.get("kind", "file")),
                    metadata=cast(Mapping[str, Any], item),
                )
        raise KeyError(f"artifact not found: {name}")

    def metrics(self) -> dict[str, float]:
        path = self.path / "metrics_summary.json"
        return cast(dict[str, float], json.loads(path.read_text(encoding="utf-8")))

    def metric(self, name: str) -> float | None:
        return self.metrics().get(name)


__all__ = ["ArtifactRef", "RunRef"]
