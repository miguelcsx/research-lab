# Data pipelines

`rlab` can define, build, validate, profile, compare, sample, and promote datasets.

A dataset pipeline is made of:

1. data sources;
2. transforms;
3. checks;
4. metrics;
5. a dataset variant.

## Define a data source

```python
import rlab

@rlab.data_source("project.raw")
def raw(ctx: rlab.DataContext):
    yield {"text": "research"}
    yield {"text": "lab"}
```

A source returns an iterable of records. A record is a `dict[str, JsonValue]`.

## Define a transform

```python
@rlab.data_transform("project.uppercase")
def uppercase(records, ctx: rlab.DataContext):
    for record in records:
        yield {**record, "text": str(record["text"]).upper()}
```

Transforms receive records and yield records.

## Define a check

```python
@rlab.data_check("project.nonempty")
def nonempty(records, ctx: rlab.DataContext):
    return rlab.DataCheckResult(
        success=any(True for _ in records),
        message="dataset must contain at least one record",
    )
```

Checks return either `DataCheckResult` or a dict that can be validated into one.

## Define a metric

```python
@rlab.data_metric("project.record_count")
def record_count(records, ctx: rlab.DataContext) -> float:
    return float(sum(1 for _ in records))
```

## Define a dataset variant

```python
@rlab.dataset_variant("project.clean")
def clean() -> rlab.DataPipeline:
    return rlab.DataPipeline(
        sources=("project.raw",),
        transforms=("project.uppercase",),
        checks=("project.nonempty",),
        metrics=("project.record_count",),
    )
```

## Build the dataset

```bash
rlab data build dataset:project.clean
```

The output run contains:

```text
artifacts/dataset/
├── data.jsonl
├── data_report.md
└── manifest.yaml
```

## Dataset manifest

A generated manifest includes:

- dataset name;
- version;
- inputs;
- pipeline stages;
- outputs;
- SHA-256 checksums;
- size in bytes;
- stats;
- check results;
- licenses.

Example:

```yaml
kind: dataset
name: project.clean
version: '1'
inputs:
  - project.raw
stages:
  - project.uppercase
outputs:
  data:
    kind: dataset_output
    name: data
    version: '1'
    path: data.jsonl
    sha256: ...
    size_bytes: 123
stats:
  records: 2
checks:
  project.nonempty: passed
```

## Profile a dataset

```bash
rlab data profile runs/<run-id>/artifacts/dataset/manifest.yaml
```

The profiler reports record count, fields, nulls, and text character counts.

## Sample records

```bash
rlab data sample runs/<run-id>/artifacts/dataset/manifest.yaml --n 5
```

Write to a file:

```bash
rlab data sample path/to/manifest.yaml --n 100 --output samples.jsonl
```

## Compare datasets

```bash
rlab data compare manifest_a.yaml manifest_b.yaml
rlab data diff manifest_a.yaml manifest_b.yaml
```

`compare` compares profiles. `diff` compares records.

## Promote a dataset

```bash
rlab data promote runs/<run-id>/artifacts/dataset/manifest.yaml --as project.clean --alias candidate
```

This promotes the materialized dataset file into the artifact store as:

```text
artifact:dataset/project.clean@candidate
```

## Data ablations

```bash
rlab data ablate dataset:project.clean --factor dedup=true,false --factor source=web,books
```

Python:

```python
ablation = rlab.DataAblation(
    base="dataset:project.clean",
    factors={
        "dedup": [True, False],
        "source": ["web", "books"],
    },
)
variants = ablation.variants()
```

## Genealogy

Use `DataGenealogyGraph` to track dataset parent-child relationships.

```python
from rlab.data.genealogy import DataGenealogyGraph

g = DataGenealogyGraph(Path(".rlab/genealogy.db"))
g.add_edge("clean_v2", "raw_v1", transform="dedup+normalize")
g.ancestors("clean_v2")
```

## Best practices

- Treat manifests as contracts.
- Keep dataset versions immutable.
- Promote only datasets that passed checks.
- Record licenses before publication.
- Use explicit names for sources and transforms.
- Make transforms streaming when possible.
- Avoid global state inside sources and transforms.
