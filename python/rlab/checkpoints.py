"""Atomic, framework-agnostic checkpoint lifecycle management."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Protocol, TypeVar

from ._typing import JsonObject

StateT = TypeVar("StateT")


class CheckpointSerializer(Protocol[StateT]):
    def write(self, path: Path, state: StateT) -> JsonObject: ...

    def read(self, path: Path) -> StateT: ...

    def validate(self, path: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    keep_last: int | None = None
    keep_best: bool = True
    keep_milestones: bool = True

    def __post_init__(self) -> None:
        if self.keep_last is not None and self.keep_last < 1:
            raise ValueError("keep_last must be positive")


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    name: str
    path: Path
    step: int
    metric: float | None
    milestone: bool


class CheckpointManager(Generic[StateT]):
    """Coordinates atomic writes, aliases, validation, and retention."""

    def __init__(
        self,
        root: str | Path,
        serializer: CheckpointSerializer[StateT],
        *,
        retention: RetentionPolicy = RetentionPolicy(),
    ) -> None:
        self.root = Path(root)
        self.serializer = serializer
        self.retention = retention
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        name: str,
        state: StateT,
        *,
        step: int,
        metric: float | None = None,
        milestone: bool = False,
    ) -> CheckpointRecord:
        if not name or "/" in name or "\\" in name:
            raise ValueError(f"invalid checkpoint name: {name!r}")
        target = self.root / name
        if target.exists():
            raise FileExistsError(f"checkpoint already exists: {target}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=self.root))
        try:
            files = self.serializer.write(temporary, state)
            manifest: JsonObject = {
                "schema_version": 1,
                "name": name,
                "step": step,
                "metric": metric,
                "milestone": milestone,
                "files": files,
            }
            _write_json(temporary / "checkpoint.json", manifest)
            self.serializer.validate(temporary)
            os.replace(temporary, target)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        record = CheckpointRecord(name, target, step, metric, milestone)
        self._alias("latest", target)
        # Read records once and reuse for both best-detection and pruning.
        all_records = self.records()
        if metric is not None and self._is_best_among(metric, all_records):
            self._alias("best", target)
        self._prune(all_records)
        return record

    def load(self, reference: str | Path = "latest") -> StateT:
        path = Path(reference)
        if not path.is_absolute():
            path = self.root / path
        resolved = path.resolve()
        self.serializer.validate(resolved)
        return self.serializer.read(resolved)

    def records(self) -> tuple[CheckpointRecord, ...]:
        records: list[CheckpointRecord] = []
        for path in self.root.iterdir():
            manifest_path = path / "checkpoint.json"
            if path.is_symlink() or not manifest_path.is_file():
                continue
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            records.append(
                CheckpointRecord(
                    name=str(value["name"]),
                    path=path,
                    step=int(value["step"]),
                    metric=(
                        float(value["metric"])
                        if value.get("metric") is not None
                        else None
                    ),
                    milestone=bool(value.get("milestone", False)),
                )
            )
        return tuple(sorted(records, key=lambda item: item.step))

    def prune(self) -> None:
        self._prune(self.records())

    def _prune(self, records: tuple[CheckpointRecord, ...]) -> None:
        keep = {
            alias.resolve()
            for alias_name in ("latest", "best")
            if (alias := self.root / alias_name).exists()
        }
        if self.retention.keep_last is not None:
            keep.update(
                record.path.resolve() for record in records[-self.retention.keep_last :]
            )
        if self.retention.keep_milestones:
            keep.update(record.path.resolve() for record in records if record.milestone)
        if self.retention.keep_last is None:
            keep.update(record.path.resolve() for record in records)
        for record in records:
            if record.path.resolve() not in keep:
                shutil.rmtree(record.path)

    def _is_best_among(
        self, metric: float, records: tuple[CheckpointRecord, ...]
    ) -> bool:
        best = self.root / "best"
        if not best.exists():
            return True
        best_path = best.resolve()
        for record in records:
            if record.path.resolve() == best_path:
                return record.metric is None or metric < record.metric
        return True

    def _alias(self, name: str, target: Path) -> None:
        temporary = self.root / f".{name}.tmp"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(target.name, target_is_directory=True)
        os.replace(temporary, self.root / name)


def _write_json(path: Path, value: JsonObject) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


__all__ = [
    "CheckpointManager",
    "CheckpointRecord",
    "CheckpointSerializer",
    "RetentionPolicy",
]
