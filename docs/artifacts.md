# Artifacts and lineage

Artifacts are promoted outputs. They are stored in a content-addressed artifact store.

Run artifacts are staged under `.rlab/runs/<run-id>/artifacts`.
`rlab runs show <run-id>` lists their references.

## Promote an artifact

```bash
rlab artifact promote outputs/model.pt --as model:small --version 1 --alias candidate
```

## Describe an artifact

```bash
rlab artifact describe artifact:model/small@1
rlab artifact describe artifact:model/small@candidate
```

## Artifact store layout

```text
.rlab/artifacts/
├── .index.jsonl
├── objects/
│   └── <sha-prefix>/<sha-rest>
└── model/
    ├── small@1.yaml
    └── small/
        └── candidate
```

## Aliases

Aliases are lifecycle labels, not scientific identity.

Recommended aliases:

| Alias | Meaning |
|---|---|
| `candidate` | Promising but not validated |
| `validated` | Passed project checks |
| `approved` | Approved for team use |
| `paper` | Used in a paper/release |
| `latest` | Convenience only |

Cite immutable versions in papers, not `latest`.

## Lineage

```bash
rlab graph lineage run:<run-id>
rlab impact artifact:dataset/clean@1
rlab invalidate artifact:dataset/clean@1 --reason "contaminated source"
```

Invalidation records an audit event and can mark downstream runs stale when the run directories are available.
