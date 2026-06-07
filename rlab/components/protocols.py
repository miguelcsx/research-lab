from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from rlab.context.runtime import RuntimeContext
from rlab.typing import Record


@runtime_checkable
class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, ids: list[int]) -> str: ...


class Model(Protocol):
    def __call__(self, inputs: Any) -> Any: ...


class DatasetSource(Protocol):
    def read(self, ctx: RuntimeContext) -> Iterable[Record]: ...


class Trainer(Protocol):
    def train(self, ctx: RuntimeContext) -> dict[str, float]: ...


class ArtifactProducer(Protocol):
    def artifacts(self) -> dict[str, str]: ...
