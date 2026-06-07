import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from rlab.typing import Record


def write_jsonl(path: Path, records: Iterable[Record]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> Iterator[Record]:
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)
