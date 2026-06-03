# research-lab

Minimal research workbench for quickly testing ideas, benchmarking atomic components, training/evaluating models, and reproducing runs.

Core concepts:

```txt
components/    reusable building blocks
benchmarks/    atomic/component-level measurements
evaluations/   final model benchmark suites and baseline comparisons
recipes/       reusable assemblies for models/data/training/eval
experiments/   research questions and ablations
runs/          reproducible evidence
artifacts/     final reports, tables, plots
```

## Install

```bash
uv sync
```

## Smoke test

```bash
uv run pytest
uv run python scripts/bench.py --target tokenizer:byte --bench tokenizer.compression --data recipes/data/tiny_text.py
uv run python scripts/eval.py --suite quick_lm --model baseline:constant
uv run python scripts/run.py experiments/001_tokenizers.py
```

## Add a component

Create a file under `components/<kind>/`, register it with `@registry.register(ComponentKind.TOKENIZER, "name")`, then reference it from recipes, benchmarks, or experiments.

## Add a benchmark

Create a file under `benchmarks/<kind>/`, register it with `@registry.register_benchmark("kind.name", TargetKind.TOKENIZER)`, implement `run(target, ctx)`.

## Add a final evaluation

Create a suite in `evaluations/suites/` using `EvaluationSuite`. It can compare local checkpoints, Hugging Face models, and baselines through adapters in `evaluations/baselines/`.
