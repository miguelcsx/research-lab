from rlab.benchmarks.context import BenchmarkContext
from rlab.components.protocols import Tokenizer


def count_tokens(target: Tokenizer, ctx: BenchmarkContext) -> dict[str, float]:
    del ctx
    return {"tokens": float(len(target.encode("test")))}
