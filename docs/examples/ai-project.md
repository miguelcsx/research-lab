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

def score(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"score": float(model(None))}

@rlab.suite("project.quick")
def quick() -> rlab.EvaluationSuite:
    return rlab.EvaluationSuite(
        tasks=(rlab.EvaluationTask(name="score", evaluator=score),),
    )
```

## Data pipeline

```python
# ingest/tiny.py
import rlab

@rlab.data_source("project.tiny_source")
def source(ctx: rlab.DataContext):
    yield {"text": "research"}
    yield {"text": "lab"}

@rlab.data_transform("project.uppercase")
def uppercase(records, ctx: rlab.DataContext):
    for record in records:
        yield {**record, "text": str(record["text"]).upper()}

@rlab.data_check("project.nonempty")
def nonempty(records, ctx: rlab.DataContext):
    return rlab.DataCheckResult(success=any(True for _ in records))

@rlab.data_metric("project.record_count")
def record_count(records, ctx: rlab.DataContext) -> float:
    return float(sum(1 for _ in records))

@rlab.dataset_variant("project.tiny")
def tiny() -> rlab.DataPipeline:
    return rlab.DataPipeline(
        sources=("project.tiny_source",),
        transforms=("project.uppercase",),
        checks=("project.nonempty",),
        metrics=("project.record_count",),
    )
```

## Experiment

```python
# experiments/smoke.py
import rlab

@rlab.experiment("ai_smoke")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="Does the generated AI project execute end to end?",
        matrix={
            "target": ["tokenizer:project.byte"],
            "model": ["model:project.constant"],
        },
        benchmarks=("project.tokenizer.length",),
        evaluations=("project.quick",),
        metrics=("project.tokenizer.length.tokens", "project.quick.score.score"),
    )
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
