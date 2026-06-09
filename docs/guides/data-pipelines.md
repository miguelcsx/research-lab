# Data pipelines

`rlab` builds datasets from immutable, typed recipes. A recipe declares a source,
stages, checks, metrics, and sinks as plain Python functions; the runtime owns
execution, output validation, manifests, checksums, lineage, and run capture.

## Define a dataset

Decorate a source function with `@rlab.dataset`. The function produces the raw
records; stages transform them in order.

```python
from collections.abc import Iterable

import rlab


def strip(
    records: Iterable[dict[str, object]],
    ctx: rlab.DataContext,
) -> Iterable[dict[str, object]]:
    del ctx
    for record in records:
        yield {**record, "text": str(record["text"]).strip()}


def nonempty(rows: list[dict[str, object]], ctx: rlab.DataContext) -> rlab.CheckResult:
    del ctx
    return rlab.CheckResult(bool(rows))


def record_count(rows: list[dict[str, object]], ctx: rlab.DataContext) -> int:
    del ctx
    return len(rows)


@rlab.dataset(
    "project.clean",
    stages=(strip,),
    checks=(nonempty,),
    metrics=(record_count,),
)
def source(ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
    del ctx
    yield {"text": "  research  "}
    yield {"text": "lab"}
```

Build it with:

```bash
rlab data build dataset:project.clean
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Dataset ID used by CLI and manifests |
| `stages` | `tuple[fn, ...]` | `()` | Pipeline transforms applied in order |
| `sinks` | `tuple[DataSink, ...]` | `(JsonlSink(),)` | Where to write the output |
| `checks` | `tuple[fn, ...]` | `()` | Validation functions run after all stages |
| `metrics` | `tuple[fn, ...]` | `()` | Measurement functions recorded in the manifest |
| `version` | `str` | `"1"` | Version recorded in the manifest |
| `description` | `str` | `""` | Human-readable description |
| `tags` | `tuple[str, ...]` | `()` | Optional registry tags |

Function names become their IDs in the manifest. Lambdas are rejected — define
named functions so manifests stay stable and readable.

## Built-in sinks and sources

Use built-in sources inside the decorated function:

```python
@rlab.dataset("corpus.hf", stages=(clean,))
def source(ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
    yield from rlab.HuggingFaceSource("squad").read(ctx)
```

Available sinks and sources:

- `rlab.JsonlSink` — default output sink (writes `data.jsonl`)
- `rlab.JsonlSource` — read from an existing JSONL file
- `rlab.TextFileSource` — read plain-text lines
- `rlab.HuggingFaceSource` — stream from Hugging Face datasets (requires `rlab[hf]`)
- `rlab.materialize()` — idempotent JSONL download helper

## Custom sinks

Implement the `DataSink` protocol as a frozen dataclass:

```python
from rlab.data.ids import OutputId

@dataclass(frozen=True)
class ParquetSink:
    id: OutputId = OutputId("parquet")
    path: Path = Path("data.parquet")

    def write(self, records, ctx: rlab.DataContext) -> rlab.SinkResult:
        ...
        return rlab.SinkResult(outputs={self.id: written_path})
```

Pass it via `sinks=(ParquetSink(),)`.

## Manifest behavior

The generated manifest records:

- source and stage IDs (derived from function names);
- output paths, directory flags, sizes, and SHA-256 checksums;
- check statuses and metrics;
- licenses returned by sinks.

Keep function names stable, stages deterministic, and output files immutable after
the manifest is written.
