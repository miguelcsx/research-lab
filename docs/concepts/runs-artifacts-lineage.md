# Runs, artifacts, and lineage

`rlab` separates three related concepts:

- a **run** is an execution record;
- an **artifact** is a reusable promoted output;
- **lineage** describes dependency relationships.

## Runs

A run is created by:

```bash
rlab run experiments/exp.py
rlab bench tokenizer:project.byte project.tokenizer.length
rlab eval project.quick --model model:project.constant
rlab data build dataset:project.tiny
```

A run contains everything needed to inspect what happened:

| File/folder | Meaning |
|---|---|
| `run.yaml` | Manifest with operation, status, timestamps, parameters, tags, parent run |
| `status.txt` | Current lifecycle status |
| `params.json` | Parameters recorded during the run |
| `metrics.jsonl` | Streaming metric events |
| `metrics_summary.json` | Latest value per metric |
| `results.json` | Final structured result payload |
| `report.md` | Human-readable summary |
| `notes.jsonl` | Researcher notes |
| `logs/` | Error logs and external command logs |
| `tables/` | CSV/JSON tables |
| `figures/` | Saved figures |
| `artifacts/` | Run-local artifacts |
| `reproducibility/` | Git, env, lockfile, command metadata |

## Run lifecycle

Possible statuses:

```text
created
planned
running
completed
failed
cancelled
stale
reproduced
```

Use stale when upstream data, code, or artifact changes invalidate a prior result.

## Artifacts

Artifacts are promoted outputs stored under the artifact store. Promotion copies a file or directory into content-addressed storage and records metadata.

CLI example:

```bash
rlab artifacts promote outputs/model.pt --as model:small --version 1 --alias candidate
rlab artifacts pull artifact:model/small@candidate
rlab artifacts list
```

Python example:

```python
from rlab.artifacts.service import promote_path

promote_path(
    runtime,
    Path("outputs/model.pt"),
    artifact_kind="model",
    name="small",
    version="1",
    alias="candidate",
)
```

## Artifact store layout

Artifacts are stored by SHA-256 under:

```text
artifacts/
├── .index.sqlite3
├── objects/
│   └── ab/
│       └── cdef...
├── model/
│   └── small@1.yaml
└── model/
    └── small/
        └── candidate
```

The content-addressed object path prevents accidental mutation of promoted artifacts.

## Lineage

Lineage stores directed edges such as:

```text
dataset:raw -> dataset:clean
dataset:clean -> model:v1
model:v1 -> report:final
```

Use lineage to answer:

- What produced this artifact?
- What downstream runs are affected if this dataset changes?
- Which reports depend on a model?
- Which models used a contaminated data source?

Example:

```python
from rlab.artifacts.lineage import ArtifactLineageGraph

graph = ArtifactLineageGraph(Path(".rlab/lineage.db"))
graph.add_edge("dataset:raw_v1", "dataset:clean_v1")
graph.add_edge("dataset:clean_v1", "model:small_v1")
graph.descendants("dataset:raw_v1")
```

CLI:

```bash
rlab impact dataset:raw_v1
rlab invalidate dataset:raw_v1 --reason "contamination discovered"
```

## Invalidation

Invalidation records an audit event and marks affected downstream runs stale when possible.

```bash
rlab invalidate dataset:clean_v1 --reason "schema bug in filtering step" --by miguel
```

Use invalidation when results remain historically useful but should no longer be treated as current evidence.
