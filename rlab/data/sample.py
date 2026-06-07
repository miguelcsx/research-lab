from collections.abc import Iterable

from rlab.typing import Record


def sample_records(records: Iterable[Record], count: int) -> tuple[Record, ...]:
    sample: list[Record] = []
    for record in records:
        if len(sample) == count:
            break
        sample.append(record)
    return tuple(sample)
