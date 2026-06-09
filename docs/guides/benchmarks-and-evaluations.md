# Benchmarks and evaluations

Benchmarks and evaluations are related but distinct.

A **benchmark** measures one target component. An **evaluation suite** measures a model or system across one or more tasks.

## Benchmarks

Define a benchmark:

```python
import rlab

@rlab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    return {"tokens": float(len(target.encode("research")))}
```

Run it:

```bash
rlab bench tokenizer:project.byte project.tokenizer.length
```

Repeat and warm up:

```bash
rlab bench tokenizer:project.byte project.tokenizer.length --warmup 2 --repeat 10
```

The service averages repeated metrics.

## BenchmarkContext

Benchmark functions receive:

```python
class BenchmarkContext:
    runtime: RuntimeContext
    benchmark: str
    target: str
    data: str | None
    params: dict[str, JsonValue]
```

Use it to access runtime paths, parameters, manifests, or run helpers.

## Return types

A benchmark can return:

```python
dict[str, float]
rlab.BenchmarkResult
rlab.ResultBundle
```

Preferred for simple measurements:

```python
return {"latency_ms": 12.3, "tokens": 8.0}
```

Preferred for richer outputs:

```python
return rlab.ResultBundle(
    metrics=(rlab.Metric(name="latency_ms", value=12.3, unit="ms"),)
)
```

## Evaluations

Define tasks directly on their suite:

```python
@rlab.evaluation("project.quick", "score")
def score(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    del ctx
    return {"score": float(model(None))}

@rlab.evaluation("project.quick", "confidence")
def confidence(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    del model, ctx
    return {"confidence": 0.9}
```

Tasks with the same suite name are composed in declaration order. No suite
factory is required.

Run it:

```bash
rlab eval project.quick --model model:project.constant
```

With options:

```bash
rlab eval project.quick \
  --model model:project.constant \
  --baseline model:project.baseline \
  --split validation \
  --limit 100 \
  --batch-size 8 \
  --device cpu \
  --save-predictions
```

## Evaluation result format

An evaluation produces:

```python
EvaluationResult(
    suite="project.quick",
    model="model:project.constant",
    tasks=(
        TaskResult(task="score", metrics={"score": 1.0}),
    ),
)
```

Metrics are recorded as:

```text
score.score
```

Meaning:

```text
<task-name>.<metric-name>
```

## Baselines

`rlab` includes simple baselines:

```python
from rlab.evaluations.baseline import ConstantBaseline, MajorityBaseline

constant = ConstantBaseline(0)
majority = MajorityBaseline(("positive", "negative", "positive"))
```

You can also register named baselines:

```bash
rlab baselines add gpt2_base --metric accuracy --value 0.82 --description "GPT-2 baseline"
rlab baselines list
rlab baselines compare <run-id>
```

## Leaderboards

```python
from rlab.evaluations.leaderboard import leaderboard

board = leaderboard("project.quick", (result_a, result_b))
```

This produces a `LeaderboardResult` with model names mapped to task metrics.

## External evaluation suites

Use an external suite when evaluation must run through a separate command, repository, or official script.

```python
rlab.external_evaluation(
    "project.official",
    command=rlab.ExternalCommand(
        args=("python", "official_eval.py", "--model", "{model}"),
        cwd=Path("."),
        timeout_seconds=600,
    ),
    parser="json",
    output=Path("metrics.json"),
)
```

Run:

```bash
rlab eval project.official --model hf:gpt2 --external-runner local
```

Supported external runners in core:

```text
local
subprocess
docker
```

Docker requires `launcher.docker_image` in `lab.toml`.

## Choosing benchmark vs evaluation

Use a benchmark when:

- there is one target component;
- the metric is atomic;
- repeated timing/measurement matters;
- you want to compare interchangeable implementations.

Use an evaluation suite when:

- there are one or more tasks;
- model behavior is measured on examples;
- baselines or leaderboards matter;
- output metrics are task-scoped.
