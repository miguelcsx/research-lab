from collections.abc import Iterable

from rlab.typing import Record


def record_key(record: Record) -> str:
    return repr(sorted(record.items()))


def diff_records(left: Iterable[Record], right: Iterable[Record]) -> dict[str, tuple[Record, ...]]:
    left_map = {record_key(record): record for record in left}
    right_map = {record_key(record): record for record in right}
    removed = tuple(left_map[key] for key in left_map.keys() - right_map.keys())
    added = tuple(right_map[key] for key in right_map.keys() - left_map.keys())
    kept = tuple(left_map[key] for key in left_map.keys() & right_map.keys())
    return {"removed": removed, "added": added, "kept": kept}
