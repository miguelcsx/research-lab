from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar, cast

from rlab.constants import EntryKind
from rlab.data.context import DataContext
from rlab.data.ids import OutputId
from rlab.data.model import SinkResult
from rlab.registry.decorators import register
from rlab.registry.store import Registry
from rlab.typing import JsonValue

RecordT = TypeVar("RecordT")
Serializer = Callable[[RecordT], Mapping[str, JsonValue]]


@dataclass(frozen=True, slots=True)
class JsonlSink(Generic[RecordT]):
    id: OutputId = OutputId("data")
    path: Path = Path("data.jsonl")
    serializer: Serializer[RecordT] | None = None

    def write(self, records: Sequence[RecordT], ctx: DataContext) -> SinkResult:
        path = ctx.work_dir / self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(
                    json.dumps(
                        self._serialize(record),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                stream.write("\n")
        return SinkResult(
            outputs={self.id: path},
            stats={"records": len(records)},
        )

    def _serialize(self, record: RecordT) -> Mapping[str, JsonValue]:
        if self.serializer is not None:
            return self.serializer(record)
        if isinstance(record, Mapping):
            return record
        if is_dataclass(record):
            return cast(Mapping[str, JsonValue], asdict(cast(Any, record)))
        model_dump = getattr(record, "model_dump", None)
        if callable(model_dump):
            value = model_dump(mode="json")
            if isinstance(value, Mapping):
                return value
        raise TypeError(f"JsonlSink cannot serialize {type(record).__name__}")


def register_builtin_sinks(registry: Registry) -> None:
    register(
        registry,
        EntryKind.SINK,
        "rlab.jsonl",
        JsonlSink,
        version="1.0.0",
        package="rlab",
        declared_by=JsonlSink,
    )
