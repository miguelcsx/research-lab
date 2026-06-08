# Artifacts, lineage, and invalidation

Artifacts let you promote outputs from runs into reusable, versioned storage.

## Promote a path

```bash
rlab artifacts promote outputs/model.pt --as model:small --version 1 --alias candidate
```

Equivalent Python:

```python
from pathlib import Path
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

## Pull an artifact

```bash
rlab artifacts pull artifact:model/small@candidate
```

## Describe artifacts

```bash
rlab artifacts list
rlab artifacts describe artifact:model/small@1
```

## Deprecate or delete

```bash
rlab artifacts deprecate artifact:model/small@1
rlab artifacts delete artifact:model/small@1
```

Deprecation keeps the record but marks it unusable. Delete removes the index row and stored object if possible.

## Alias lifecycle

Recommended aliases:

| Alias | Meaning |
|---|---|
| `candidate` | Promising but not validated |
| `validated` | Passed project checks |
| `approved` | Approved for team use |
| `paper` | Used in a paper/release |
| `latest` | Convenience alias, not a scientific identity |

Do not cite `latest` in papers. Cite immutable versions or frozen runs.

## Lineage graph

```python
from rlab.artifacts.lineage import ArtifactLineageGraph

lineage = ArtifactLineageGraph(Path(".rlab/lineage.db"))
lineage.add_edge("dataset:raw_v1", "dataset:clean_v1")
lineage.add_edge("dataset:clean_v1", "model:small_v1")
lineage.add_edge("model:small_v1", "report:paper_table_2")
```

Inspect:

```python
lineage.ancestors("model:small_v1")
lineage.descendants("dataset:raw_v1")
```

## Impact

```bash
rlab impact dataset:raw_v1
```

This shows upstream and downstream items known to the lineage store.

## Invalidate

```bash
rlab invalidate dataset:raw_v1 \
  --reason "Source contained duplicates across train/test split" \
  --by miguel
```

Invalidation records an audit event and marks downstream runs stale when their run directories can be found.

## Audit trail

```python
from rlab.artifacts.audit import AuditTrail

audit = AuditTrail(Path(".rlab/audit.jsonl"))
audit.record(
    "invalidate",
    "dataset:raw_v1",
    actor="miguel",
    reason="contamination",
)
events = audit.replay()
```

Audit events are JSON Lines and are append-only by convention.

## Recommended policy

- Promote artifacts only after a successful run.
- Never overwrite an artifact version to mean different content.
- Use aliases for maturity, not identity.
- Record lineage for every important artifact.
- Invalidate instead of silently deleting flawed evidence.
