from collections.abc import Callable, Iterable

from rlab.data.context import DataContext
from rlab.typing import Record

DataMetric = Callable[[Iterable[Record], DataContext], int | float]
