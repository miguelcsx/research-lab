from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from rlab.data.context import DataContext
from rlab.data.ids import SourceId
from rlab.typing import JsonValue, Record

RowMapper = Callable[[Mapping[str, Any], int], Record | Iterable[Record] | None]


@dataclass(frozen=True, slots=True)
class TextFileSource:
    id: SourceId
    path: Path
    encoding: str = "utf-8"
    field: str = "text"

    def read(self, ctx: DataContext) -> Iterator[Record]:
        path = _resolve(ctx, self.path)
        with path.open(encoding=self.encoding) as stream:
            for index, line in enumerate(stream):
                yield {"id": index, self.field: line.rstrip("\n")}


@dataclass(frozen=True, slots=True)
class JsonlSource:
    id: SourceId
    path: Path
    encoding: str = "utf-8"

    def read(self, ctx: DataContext) -> Iterator[Record]:
        path = _resolve(ctx, self.path)
        with path.open(encoding=self.encoding) as stream:
            for line in stream:
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise TypeError(f"JSONL row must be an object: {path}")
                    yield {str(key): _json_value(item) for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class HuggingFaceSource:
    id: SourceId
    dataset: str
    split: str = "train"
    config: str | None = None
    data_files: tuple[str, ...] = ()
    streaming: bool = False
    mapper: RowMapper | None = None
    max_records: int | None = None

    def read(self) -> Iterator[Record]:
        try:
            load_dataset = import_module("datasets").load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "Hugging Face sources require the optional 'rlab[hf]' dependency"
            ) from exc

        kwargs: dict[str, object] = {
            "path": self.dataset,
            "split": self.split,
            "streaming": self.streaming,
        }
        if self.config is not None:
            kwargs["name"] = self.config
        if self.data_files:
            kwargs["data_files"] = list(self.data_files)
        rows = load_dataset(**kwargs)
        for index, row in enumerate(rows):
            if self.max_records is not None and index >= self.max_records:
                return
            if not isinstance(row, Mapping):
                raise TypeError(f"Hugging Face row {index} is not a mapping")
            mapped = self.mapper(row, index) if self.mapper else _record(row)
            if mapped is None:
                continue
            if isinstance(mapped, Mapping):
                yield dict(mapped)
            else:
                yield from mapped


def materialize(
    records: Iterable[Record],
    destination: Path,
    *,
    overwrite: bool = False,
) -> Path:
    if destination.exists() and not overwrite:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    return destination


def _resolve(ctx: DataContext, path: Path) -> Path:
    return path if path.is_absolute() else ctx.runtime.paths.root / path


def _record(row: Mapping[str, Any]) -> Record:
    return {str(key): _json_value(value) for key, value in row.items()}


def _json_value(value: Any) -> JsonValue:
    return cast(JsonValue, value)
