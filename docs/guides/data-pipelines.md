# Data pipelines

`rlab` data builds are immutable registry declarations. Sources, stages, pipelines,
datasets, sinks, checks, and metrics have explicit names and semantic versions.

```python
from collections.abc import Iterable
from dataclasses import dataclass

import rlab


@rlab.source("project.raw")
@dataclass(frozen=True, slots=True)
class RawSource:
    limit: int = 2

    def read(self, ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
        del ctx
        yield from ({"text": " research "}, {"text": ""})[: self.limit]


@rlab.transform("text.strip")
@dataclass(frozen=True, slots=True)
class StripText:
    def apply(
        self,
        record: dict[str, object],
        ctx: rlab.DataContext,
    ) -> rlab.DataDecision[dict[str, object]]:
        del ctx
        text = str(record["text"]).strip()
        if not text:
            return rlab.data_drop("empty")
        return rlab.data_update({**record, "text": text}, reason="stripped")


@rlab.pipeline(
    "project.clean",
    stages=(rlab.use("transform:text.strip"),),
)
class CleanPipeline:
    pass


@rlab.dataset(
    "project.clean",
    source=rlab.use("source:project.raw"),
    pipeline="pipeline:project.clean",
    sinks=(rlab.use("sink:rlab.jsonl"),),
    audit=rlab.AuditPolicy(
        capture_decisions=True,
        sample_reasons={"empty": 10},
    ),
)
class CleanDataset:
    pass
```

Build with a typed component override:

```bash
rlab data build dataset:project.clean --override source.limit=1
```

Unknown paths and values incompatible with the dataclass field type are rejected.
The dataset declaration's semantic version is the manifest version.

## Decisions and boundaries

Record transforms and filters return `DataDecision` using `data_keep`,
`data_update`, `data_drop`, or `data_boundary`. Boundaries bypass later
record-level stages and must be consumed by a `group` or `dedup`
stage before records reach a sink.

Grouping and deduplication stages receive iterables containing records and
`DataBoundary` values. They remain normal explicit Python algorithms wrapped
in registered frozen dataclasses.

## Auditing

Every build writes `summary.json`, `drop_reasons.csv`, `stage_summary.csv`, and
`source_summary.csv` under `artifacts/dataset/audit/`. `AuditPolicy` controls
full decision capture and bounded reason-specific samples.

```bash
rlab data audit runs/<run-id>
rlab data reasons runs/<run-id>
rlab data stage-summary runs/<run-id>
rlab data source-summary runs/<run-id>
rlab data sample-drops runs/<run-id> empty
```

## Declarative utilities

Use `patterns`, `substitute`, `classify`, `predicate`,
and `threshold` for simple policies. Complex loading, grouping, validation,
deduplication, and writing logic should remain explicit typed classes.
