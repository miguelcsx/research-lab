# Example: systems or simulation project

`rlab` is not limited to AI. You can use it for compilers, numerical methods, simulations, proof systems, chemistry pipelines, biology workflows, or engineering experiments.

This example benchmarks two solvers.

## Components

```python
# components/solvers.py
import rlab

@rlab.component("solver", "project.fdtd")
class FdtdSolver:
    def solve(self, nx: int) -> dict[str, float]:
        return {"l2_error": 1.0 / nx, "runtime_seconds": nx / 1000}

@rlab.component("solver", "project.spectral")
class SpectralSolver:
    def solve(self, nx: int) -> dict[str, float]:
        return {"l2_error": 1.0 / (nx * nx), "runtime_seconds": nx / 500}
```

## Benchmark

```python
# benchmarks/solvers.py
import rlab

@rlab.benchmark("project.solver_error", target="solver")
def solver_error(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    nx = int(ctx.params.get("nx", 128))
    result = target.solve(nx)
    return {
        "l2_error": float(result["l2_error"]),
        "runtime_seconds": float(result["runtime_seconds"]),
    }
```

## Experiment

```python
# experiments/solver_sweep.py
import rlab

@rlab.experiment("solver_sweep")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="Which solver gives the best error/runtime tradeoff?",
        hypothesis="The spectral solver has lower error but higher runtime.",
        matrix={
            "target": ["solver:project.fdtd", "solver:project.spectral"],
            "nx": [64, 128, 256],
        },
        benchmarks=("project.solver_error",),
        metrics=("project.solver_error.l2_error", "project.solver_error.runtime_seconds"),
        decision_criteria="Select the solver with lowest error under the runtime budget.",
    )
```

## Commands

```bash
rlab run experiments/solver_sweep.py --dry-run
rlab run experiments/solver_sweep.py
rlab compare runs/ --metric project.solver_error.l2_error
```

## Add power estimation

```bash
rlab plan power --effect-size 0.05 --variance 1.0 --alpha 0.05 --power 0.8
```

## Add budget estimation

```bash
rlab plan cost experiments/solver_sweep.py --seconds-per-job 60 --storage-gb-per-job 0.5
```

## External compiler example

```python
import rlab

@rlab.workflow("compiler.benchmark")
def compiler_benchmark() -> rlab.Workflow:
    return rlab.Workflow(
        steps=(
            rlab.ExternalStep(
                name="compile",
                command=("clang", "-O3", "main.c", "-o", "main"),
                timeout_seconds=60,
            ),
            rlab.ExternalStep(
                name="run",
                command=("./main",),
                parser="project.parsers:parse_runtime",
                timeout_seconds=60,
            ),
        )
    )
```
