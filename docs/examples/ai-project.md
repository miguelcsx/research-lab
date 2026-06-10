# Example: AI project

This example defines a tokenizer, model, benchmark, evaluation suite, data pipeline, and experiment.

## `lab.toml`

```toml
[project]
name = "ai-example"

[modules]
load = [
  "components.tokenizers",
  "components.models",
  "benchmarks.tokenizers",
  "evaluations.quick",
  "ingest.tiny",
  "experiments.smoke",
]
```

## Component: tokenizer

```python
# components/tokenizers.py
import rlab

@rlab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()
```

## Component: model

```python
# components/models.py
import rlab

@rlab.component("model", "project.constant")
class ConstantModel:
    def __call__(self, inputs: object) -> float:
        return 1.0
```

## Benchmark

```python
# benchmarks/tokenizers.py
import rlab

@rlab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    return {"tokens": float(len(target.encode("research")))}
```

## Evaluation

```python
# evaluations/quick.py
import rlab

@rlab.evaluation("project.quick", "score")
def score(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    del ctx
    return {"score": float(model(None))}
```

## Data pipeline

```python
# ingest/tiny.py
from collections.abc import Iterable
from dataclasses import dataclass

import rlab


@rlab.source("project.tiny")
@dataclass(frozen=True, slots=True)
class TinySource:
    def read(self, ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
        del ctx
        yield {"text": "research"}
        yield {"text": "lab"}


@rlab.pipeline("project.tiny", stages=())
class TinyPipeline:
    pass


@rlab.dataset(
    "project.tiny",
    source=rlab.use("source:project.tiny"),
    pipeline="pipeline:project.tiny",
    sinks=(rlab.use("sink:rlab.jsonl"),),
)
class TinyDataset:
    pass
```

## Experiment

```python
# experiments/smoke.py
import rlab

@rlab.experiment(
    "ai_smoke",
    question="Does the generated AI project execute end to end?",
    matrix={
        "target": ["tokenizer:project.byte"],
        "model": ["model:project.constant"],
    },
    benchmarks=("project.tokenizer.length",),
    evaluations=("project.quick",),
    metrics=("project.tokenizer.length.tokens", "project.quick.score.score"),
)
def experiment(ctx: rlab.RuntimeContext) -> None:
    del ctx
```

## Commands

```bash
rlab doctor
rlab discover
rlab bench tokenizer:project.byte project.tokenizer.length
rlab eval project.quick --model model:project.constant
rlab data build dataset:project.tiny
rlab run experiments/smoke.py
rlab compare runs/
```
