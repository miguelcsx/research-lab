# Data recipes

`rlab` builds datasets from immutable, typed recipes. A recipe declares sources,
stages, checks, metrics, and sinks as Python objects; the runtime owns execution,
output validation, manifests, checksums, lineage, and run capture.

## Define one recipe

```python
from collections.abc import Iterable

import rlab


def raw(ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
    del ctx
    yield {"text": "  research  "}
    yield {"text": "lab"}


def strip(
    records: Iterable[dict[str, object]],
    ctx: rlab.DataContext,
) -> Iterable[dict[str, object]]:
    del ctx
    for record in records:
        yield {**record, "text": str(record["text"]).strip()}


flow = rlab.DataFlow.from_source(
    rlab.FunctionSource(rlab.SourceId("project.raw"), raw)
).then(rlab.FunctionStage(rlab.StageId("project.strip"), strip))

CLEAN = rlab.DatasetRecipe(
    id=rlab.DatasetId("project.clean"),
    flow=flow,
    sinks=(rlab.JsonlSink(),),
    checks=(
        rlab.FunctionCheck(
            rlab.CheckId("project.nonempty"),
            lambda rows, _ctx: rlab.CheckResult(bool(rows)),
        ),
    ),
    metrics=(
        rlab.FunctionMetric(
            rlab.MetricId("project.record-count"),
            lambda rows, _ctx: len(rows),
        ),
    ),
)

rlab.register_datasets(rlab.DatasetCatalog(CLEAN))
```

Build it with:

```bash
rlab data build dataset:project.clean
```

## Reuse and variants

Recipes are immutable. Use `replace()` to derive an experiment while retaining
the same typed flow:

```python
SMALL = CLEAN.replace(id=rlab.DatasetId("project.clean-small"))
rlab.register_datasets(rlab.DatasetCatalog(CLEAN, SMALL))
```

For repeated behavior, implement the `DataSource`, `DataStage`, `DataCheck`,
`DataMetric`, or `DataSink` protocol as a small frozen dataclass. Use
`FunctionSource` and related wrappers for one-off functions.

## Built-in adapters and sinks

- `TextFileSource`
- `JsonlSource`
- `HuggingFaceSource` through the optional `rlab[hf]` dependency
- `JsonlSink`
- `materialize()` for idempotent JSONL downloads

Custom sinks may produce several files or directories by returning
`SinkResult`. Every path must exist inside `DataContext.work_dir`.

## Manifest behavior

The generated manifest records:

- recipe, source, and stage IDs;
- output paths, directory flags, sizes, and SHA-256 checksums;
- check statuses and metrics;
- licenses returned by sinks.

Keep IDs stable, stages deterministic, and output files immutable after the
manifest is written.
