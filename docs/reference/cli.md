# CLI reference

The CLI entrypoint is:

```bash
rlab
python -m rlab
uv run rlab
```

Global options:

```bash
rlab --root /path/to/project --json <command>
```

## Project and diagnostics

```bash
rlab init project <name> --template ai
rlab init new <kind> <name>
rlab doctor
rlab lint
rlab status
rlab config show
rlab config validate
rlab config paths
rlab modules list
rlab modules doctor
rlab modules reload
rlab discover
rlab discover benchmarks
```

## Run experiments

```bash
rlab run experiments/exp.py
rlab run experiments/exp.py --dry-run
rlab run experiments/exp.py --seed 42
rlab run experiments/exp.py --name candidate_v2
rlab run experiments/exp.py --tag ablation --tag paper
rlab run experiments/exp.py --notes "initial sweep"
rlab run experiments/exp.py --launcher subprocess
rlab run experiments/exp.py --resume runs/<run-id>
rlab run experiments/exp.py --only 0003
rlab run experiments/exp.py --set launcher.timeout_seconds=600
```

## Benchmarks

```bash
rlab bench <target-ref> <benchmark-name>
rlab bench tokenizer:project.byte project.tokenizer.length
rlab bench tokenizer:project.byte project.tokenizer.length --repeat 10 --warmup 2
rlab bench tokenizer:project.byte project.tokenizer.length --params key=value
rlab bench tokenizer:project.byte project.tokenizer.length --output reports/bench-run
rlab bench tokenizer:project.byte project.tokenizer.length --compare-with runs/<run-id>
```

## Evaluations

```bash
rlab eval <suite> --model <model-ref>
rlab eval project.quick --model model:project.constant
rlab eval project.quick --model model:a --baseline model:b
rlab eval project.quick --model model:a --split validation --limit 100 --batch-size 8 --device cpu
rlab eval project.official --model hf:gpt2 --external-runner local
```

## Datasets

```bash
rlab data build dataset:project.tiny
rlab data profile path/to/manifest.yaml
rlab data validate path/to/manifest.yaml
rlab data diff left.yaml right.yaml
rlab data compare a.yaml b.yaml
rlab data ablate dataset:x --factor dedup=true,false
rlab data sample manifest.yaml --n 10
rlab data sample manifest.yaml --n 100 --output sample.jsonl
rlab data lineage manifest.yaml
rlab data promote manifest.yaml --as project.tiny --alias candidate
```

## Runs

```bash
rlab runs list
rlab runs list --status completed
rlab runs list --tag paper --limit 20
rlab runs show <run-id>
rlab runs logs <run-id>
rlab runs clean --failed --dry-run
rlab runs clean --failed
rlab runs query "status = 'completed'"
rlab runs tail <run-id>
```

## Compare and diff

```bash
rlab compare runs/
rlab compare runs/ --metric accuracy
rlab compare runs/ --group-by operation
rlab compare runs/ --sort-by accuracy --descending
rlab compare runs/ --format csv --output reports/comparison.csv
rlab diff runs/a runs/b
```

## Reproduce

```bash
rlab reproduce runs/<run-id> --dry-run
rlab reproduce runs/<run-id>
rlab reproduce runs/<run-id> --strict
rlab reproduce runs/<run-id> --strict --allow-dirty
rlab reproduce runs/<run-id> --checkout
rlab reproduce runs/<run-id> --container
```

## Artifacts

```bash
rlab artifacts list
rlab artifacts promote path/to/file --as model:small --version 1 --alias candidate
rlab artifacts pull artifact:model/small@candidate
rlab artifacts describe artifact:model/small@1
rlab artifacts aliases
rlab artifacts deprecate artifact:model/small@1
rlab artifacts delete artifact:model/small@1
```

## Cache and jobs

```bash
rlab cache path
rlab cache inspect
rlab cache list
rlab cache clean
rlab cache clean --older-than 30
rlab cache prune downloads

rlab jobs start "python train.py"
rlab jobs list
rlab jobs logs <job-id>
rlab jobs cancel <job-id>
```

## Reports and paper operations

```bash
rlab report run runs/<run-id> --output reports/run.md
rlab report compare runs/ --output reports/comparison.md

rlab freeze run runs/<run-id> --as paper_main
rlab freeze lock runs/<run-id>
rlab freeze export runs/<run-id> --format repro-zip
rlab freeze methods runs/<run-id>
```

## Journal, notes, search

```bash
rlab notes add <run-id> "observation"
rlab notes list <run-id>

rlab journal decision add "Promote model v3" --run <run-id>
rlab journal decision list

rlab journal negative add "hypothesis" "tried" "reason"
rlab journal negative list
rlab journal negative search minhash

rlab journal ideas add "Try larger batch size"
rlab journal ideas list
rlab journal ideas promote <idea-id> planned

rlab search "dedup"
rlab search "accuracy" --kind run
```

## CI

```bash
rlab ci smoke
rlab ci compare --baseline <run-id> --candidate <run-id> --metric accuracy --threshold 0.01
rlab ci reproducibility-check
```

## Graph, impact, invalidation

```bash
rlab graph build
rlab graph query "SELECT * FROM graph_nodes LIMIT 10"
rlab graph lineage run:<run-id>
rlab impact dataset:raw_v1
rlab invalidate dataset:raw_v1 --reason "contamination"
```

## Exec and handoff

```bash
rlab exec --name unit_tests pytest
rlab exec --name benchmark --parser project.parsers:parse "python bench.py"
rlab handoff <run-id> --to team-b
```
