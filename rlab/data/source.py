from collections.abc import Iterable
from typing import Protocol

from rlab.data.context import DataContext
from rlab.typing import Record


class DataSource(Protocol):
    def __call__(self, ctx: DataContext) -> Iterable[Record]: ...
