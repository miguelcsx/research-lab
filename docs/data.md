# Data pipelines

`rlab` supports declarative data sources, stages, pipelines, datasets, checks, metrics, and sinks.

## Minimal data pipeline

```python
from dataclasses import dataclass
import rlab

lab = rlab.Project()

@lab.source("project.raw")
@dataclass(frozen=True, slots=True)
class RawSource:
    def read(self, ctx):
        yield {"text": " research "}
        yield {"text": ""}

@lab.transform("text.strip")
@dataclass(frozen=True, slots=True)
class StripText:
    def apply(self, record, ctx):
        text = str(record["text"]).strip()
        if not text:
            return rlab.data_drop("empty")
        return rlab.data_update({**record, "text": text}, reason="stripped")

@lab.pipeline(
    "project.clean",
    rlab.ComponentSpec.empty("transform:text.strip"),
)
class CleanPipeline:
    pass

@lab.dataset(
    "project.clean",
    source=rlab.ComponentSpec.empty("source:project.raw"),
    pipeline="pipeline:project.clean",
    sinks=(rlab.ComponentSpec.empty("sink:rlab.jsonl"),),
)
class CleanDataset:
    pass
```

Build:

```bash
rlab data build dataset:project.clean
```

## Data decisions

Stages return a `DataDecision`:

```python
rlab.data_keep(record)
rlab.data_update(record, reason="normalized")
rlab.data_drop("empty")
rlab.data_boundary(value, kind="document")
```

## Built-in JSONL source/sink

Import built-ins from data subpackages, not top-level `rlab`:

```python
from rlab.data.sources.jsonl import JsonlSource
from rlab.data.sinks.jsonl import JsonlSink
```

Built-ins are defaults, not the public top-level contract.
