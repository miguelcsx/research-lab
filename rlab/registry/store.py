from __future__ import annotations

import threading
from collections.abc import Iterable

from rlab.constants import EntryKind
from rlab.errors import RegistryConflictError, RegistryError
from rlab.registry.keys import RegistryKey
from rlab.registry.records import RegistryRecord


class Registry:
    def __init__(self, *, allow_project_overrides: bool = False) -> None:
        self._records: dict[RegistryKey, RegistryRecord] = {}
        self.allow_project_overrides = allow_project_overrides
        self._lock = threading.Lock()

    def add(self, record: RegistryRecord) -> None:
        key = RegistryKey(kind=record.kind, name=record.name)
        with self._lock:
            current = self._records.get(key)
            can_override = (
                self.allow_project_overrides
                and current is not None
                and current.package != "project"
                and record.package == "project"
            )
            same_definition = (
                current is not None
                and current.source == record.source
                and current.qualname == record.qualname
            )
            if (
                current is not None
                and current.value is not record.value
                and not can_override
                and not same_definition
            ):
                raise RegistryConflictError(f"Registry entry {key} is already defined")
            self._records[key] = record

    def get(self, kind: EntryKind, name: str) -> RegistryRecord:
        key = RegistryKey(kind=kind, name=name)
        with self._lock:
            record = self._records.get(key)
        if record is None:
            choices = ", ".join(r.name for r in self.list(kind)) or "none"
            raise RegistryError(f"Unknown {kind.value} {name!r}; available: {choices}")
        return record

    def try_get(self, kind: EntryKind, name: str) -> RegistryRecord | None:
        with self._lock:
            return self._records.get(RegistryKey(kind=kind, name=name))

    def replace(self, record: RegistryRecord) -> None:
        key = RegistryKey(kind=record.kind, name=record.name)
        with self._lock:
            if key not in self._records:
                raise RegistryError(f"Cannot replace missing registry entry {key}")
            self._records[key] = record

    def list(self, kind: EntryKind | None = None) -> tuple[RegistryRecord, ...]:
        with self._lock:
            records: Iterable[RegistryRecord] = self._records.values()
            if kind is not None:
                records = (record for record in records if record.kind is kind)
            return tuple(sorted(records, key=lambda record: (record.kind.value, record.name)))

    def conflicts(self) -> tuple[str, ...]:
        return ()

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
