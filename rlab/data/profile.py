from collections import Counter
from collections.abc import Iterable

from rlab.typing import Record


def profile_records(records: Iterable[Record]) -> dict[str, object]:
    count = 0
    fields: Counter[str] = Counter()
    nulls: Counter[str] = Counter()
    text_chars = 0
    for record in records:
        count += 1
        fields.update(record.keys())
        nulls.update(key for key, value in record.items() if value is None)
        text_chars += sum(len(value) for value in record.values() if isinstance(value, str))
    return {
        "records": count,
        "fields": dict(fields),
        "nulls": dict(nulls),
        "text_chars": text_chars,
    }
