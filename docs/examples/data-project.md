# Example: data project

This example focuses on dataset construction, validation, profiling, and promotion.

## Goal

Build a clean JSONL dataset from raw records, validate that it is non-empty, count records, inspect profile, and promote the dataset artifact.

## Data module

```python
# ingest/corpus.py
import rlab

@rlab.data_source("corpus.raw")
def raw(ctx: rlab.DataContext):
    yield {"id": "1", "text": "  Hello world  ", "source": "web"}
    yield {"id": "2", "text": "Research lab", "source": "book"}

@rlab.data_transform("corpus.strip")
def strip_text(records, ctx: rlab.DataContext):
    for row in records:
        yield {**row, "text": str(row["text"]).strip()}

@rlab.data_transform("corpus.drop_empty")
def drop_empty(records, ctx: rlab.DataContext):
    for row in records:
        if row.get("text"):
            yield row

@rlab.data_check("corpus.nonempty")
def nonempty(records, ctx: rlab.DataContext):
    count = sum(1 for _ in records)
    return rlab.DataCheckResult(
        success=count > 0,
        metrics={"records": float(count)},
        message="dataset must not be empty",
    )

@rlab.data_metric("corpus.text_chars")
def text_chars(records, ctx: rlab.DataContext) -> float:
    return float(sum(len(str(row.get("text", ""))) for row in records))

@rlab.dataset_variant("corpus.clean_v1")
def clean_v1() -> rlab.DataPipeline:
    return rlab.DataPipeline(
        sources=("corpus.raw",),
        transforms=("corpus.strip", "corpus.drop_empty"),
        checks=("corpus.nonempty",),
        metrics=("corpus.text_chars",),
    )
```

## Config

```toml
[modules]
load = ["ingest.corpus"]
```

## Build

```bash
rlab data build dataset:corpus.clean_v1
```

## Inspect

```bash
MANIFEST=runs/<run-id>/artifacts/dataset/manifest.yaml

rlab data profile "$MANIFEST"
rlab data validate "$MANIFEST"
rlab data sample "$MANIFEST" --n 5
```

## Promote

```bash
rlab data promote "$MANIFEST" --as corpus.clean_v1 --alias candidate
rlab artifacts pull artifact:dataset/corpus.clean_v1@candidate
```

## Compare versions

After changing the pipeline and building version 2:

```bash
rlab data compare manifest_v1.yaml manifest_v2.yaml
rlab data diff manifest_v1.yaml manifest_v2.yaml
```

## Record data lineage

```python
from pathlib import Path
from rlab.data.genealogy import DataGenealogyGraph

graph = DataGenealogyGraph(Path(".rlab/genealogy.db"))
graph.add_edge("corpus.clean_v1", "corpus.raw", transform="strip+drop_empty")
```
