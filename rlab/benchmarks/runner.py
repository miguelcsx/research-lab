from collections.abc import Mapping
from typing import Any

from rlab.benchmarks.context import BenchmarkContext
from rlab.benchmarks.result import BenchmarkResult
from rlab.components.builders import build_component
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.errors import RegistryError
from rlab.references.parser import parse_reference


def execute_benchmark(
    runtime: RuntimeContext,
    target: str,
    benchmark: str,
    *,
    data: str | None = None,
    params: dict[str, Any] | None = None,
) -> BenchmarkResult:
    record = runtime.registry.get(EntryKind.BENCHMARK, benchmark)
    target_reference = parse_reference(target)
    target_kind = target_reference.component_kind or target_reference.kind.value
    if record.target_kind != target_kind:
        raise RegistryError(
            f"Benchmark {benchmark!r} targets {record.target_kind!r}, not {target_kind!r}"
        )
    target_value = build_component(runtime.registry, target)
    context = BenchmarkContext(
        runtime=runtime,
        benchmark=benchmark,
        target=target,
        data=data,
        params=params or {},
    )
    result = record.value(target_value, context)
    if isinstance(result, BenchmarkResult):
        return result
    if not isinstance(result, Mapping):
        raise TypeError(f"Benchmark {benchmark!r} must return metrics or BenchmarkResult")
    return BenchmarkResult(
        metrics={
            str(name): float(value)
            for name, value in result.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
