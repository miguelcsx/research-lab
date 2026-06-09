from collections.abc import Iterable
from typing import Protocol, TypeVar, runtime_checkable

from rlab.context.runtime import RuntimeContext
from rlab.typing import Record


@runtime_checkable
class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, ids: list[int]) -> str: ...


InputT_contra = TypeVar("InputT_contra", contravariant=True)
OutputT_co = TypeVar("OutputT_co", covariant=True)


class Model(Protocol[InputT_contra, OutputT_co]):
    def __call__(self, inputs: InputT_contra) -> OutputT_co: ...


class DatasetSource(Protocol):
    def read(self, ctx: RuntimeContext) -> Iterable[Record]: ...


class Trainer(Protocol):
    def train(self, ctx: RuntimeContext) -> dict[str, float]: ...


class ArtifactProducer(Protocol):
    def artifacts(self) -> dict[str, str]: ...
