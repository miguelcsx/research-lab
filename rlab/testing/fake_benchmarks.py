from typing import Protocol

from rlab.benchmarks.context import BenchmarkContext


class _Encoder(Protocol):
    def encode(self, text: str) -> list[int]: ...


def count_tokens(target: _Encoder, ctx: BenchmarkContext) -> dict[str, float]:
    del ctx
    return {"tokens": float(len(target.encode("test")))}
