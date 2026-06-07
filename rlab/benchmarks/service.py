from pathlib import Path
from typing import Any

from rlab.benchmarks.runner import execute_benchmark
from rlab.context.runtime import RuntimeContext
from rlab.runs.session import RunSession


def run_benchmark(  # noqa: PLR0913
    runtime: RuntimeContext,
    target: str,
    benchmark: str,
    *,
    data: str | None = None,
    params: dict[str, Any] | None = None,
    repeat: int = 1,
    warmup: int = 0,
) -> Path:
    session = RunSession(
        runtime,
        "benchmark",
        benchmark,
        {"target": target, "benchmark": benchmark, "data": data, "repeat": repeat},
    )
    active = session.start()
    try:
        for _ in range(warmup):
            execute_benchmark(active, target, benchmark, data=data, params=params)
        results = [
            execute_benchmark(active, target, benchmark, data=data, params=params)
            for _ in range(repeat)
        ]
        metrics = {
            name: sum(result.metrics[name] for result in results) / len(results)
            for name in results[0].metrics
        }
        for name, value in metrics.items():
            session.metric(name, value, target=target, benchmark=benchmark)
        session.complete(
            {"target": target, "benchmark": benchmark, "metrics": metrics},
            "\n".join(("# Benchmark", "", *(f"- `{k}`: {v:g}" for k, v in metrics.items()))),
        )
        return session.layout.root
    except Exception as error:
        session.fail(error)
        raise
