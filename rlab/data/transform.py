from collections.abc import Iterable
from typing import Protocol

from rlab.data.context import DataContext
from rlab.typing import Record


class DataTransform(Protocol):
    def __call__(self, records: Iterable[Record], ctx: DataContext) -> Iterable[Record]: ...
