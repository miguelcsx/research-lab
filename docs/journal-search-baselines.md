# Journal, notes, baselines, and search

Research includes negative results, decisions, notes, and ideas. `rlab` keeps these as local append-only records.

## Notes

```bash
rlab notes add <run-id> "Training diverged after epoch 3."
rlab notes list <run-id>
```

Programmatic:

```python
ctx.note("Batch size 64 caused OOM on local GPU.")
```

## Decisions

```bash
rlab journal decision add "Use model v3 for the paper" --run <run-id>
rlab journal decision list
```

## Negative results

```bash
rlab journal negative add "larger batch improves loss" "batch=128" "OOM on local GPU"
rlab journal negative list
rlab journal negative search "OOM"
```

## Ideas

```bash
rlab journal ideas add "Try source-balanced data mixing"
rlab journal ideas list
rlab journal ideas promote <id> planned
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

```bash
rlab search "dedup"
rlab search "accuracy" --kind run
```

## Baselines

```bash
rlab baselines add gpt2_base --metric eval.accuracy --value 0.82 --description "GPT-2 baseline"
rlab baselines list
rlab baselines compare <run-id>
```
