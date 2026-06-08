# Journal, search, and baselines

Research is not just successful runs. `rlab` records decisions, notes, ideas, and negative results.

## Run notes

```bash
rlab notes add <run-id> "Training diverged after epoch 3."
rlab notes list <run-id>
```

Programmatic:

```python
ctx.note("Batch size 64 caused OOM on local GPU.")
```

## Decisions

Record why a run or artifact was selected:

```bash
rlab journal decision add "Promote clean_v3 because it improves accuracy and reduces duplicates" --run <run-id>
rlab journal decision list
```

A decision can include criteria in Python:

```python
from rlab.journal.decisions import add_decision

add_decision(
    Path(".rlab/decisions.jsonl"),
    "Use model_v3 for the paper.",
    selected_run="run:abc",
    criteria={"accuracy": "highest", "latency": "acceptable"},
)
```

## Negative results

Negative results are first-class research evidence.

```bash
rlab journal negative add \
  "Dedup improves validation accuracy" \
  "Tried MinHash threshold 0.8" \
  "No measurable improvement"
```

Search:

```bash
rlab journal negative search minhash
```

## Ideas

```bash
rlab journal ideas add "Try source-balanced data mixing"
rlab journal ideas list
rlab journal ideas promote <idea-id> planned
```

Idea statuses:

```text
idea
planned
running
validated
rejected
published
```

## Search

Search across indexed runs, notes, artifacts, and decisions:

```bash
rlab search "dedup"
rlab search "accuracy" --kind run
```

The search index is SQLite FTS5. The CLI rebuilds the index on first use.

## Baselines

Register a named baseline metric:

```bash
rlab baselines add gpt2_base \
  --metric eval.accuracy \
  --value 0.82 \
  --description "GPT-2 baseline on validation split"
```

List:

```bash
rlab baselines list
```

Compare a run against baselines:

```bash
rlab baselines compare <run-id>
```

## Recommended practice

- Record why decisions were made, not only what was chosen.
- Record negative results immediately.
- Link important notes to run IDs.
- Use baselines for stable reference points.
- Search before repeating old experiments.
