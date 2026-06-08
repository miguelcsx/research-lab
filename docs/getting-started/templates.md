# Project templates

`rlab init project` supports several templates. A template creates a `lab.toml`, a `pyproject.toml`, standard folders, and minimal working modules.

## Available templates

```bash
rlab init project my-project --template basic
rlab init project my-project --template ai
rlab init project my-project --template data
rlab init project my-project --template simulation
rlab init project my-project --template lean
rlab init project my-project --template systems
rlab init project my-project --template paper
```

## Template purposes

| Template | Best for |
|---|---|
| `basic` | Small experiments, library smoke tests, simple benchmarks |
| `ai` | Models, tokenizers, datasets, evaluations, benchmark loops |
| `data` | Dataset construction, data checks, profiling, ablations |
| `simulation` | Solvers, numerical methods, physical simulations, scenario sweeps |
| `lean` | Proof experiments, external Lean/Lake workflows, proof benchmarks |
| `systems` | Compilers, runtimes, performance experiments, external tools |
| `paper` | Paper reproduction packages, frozen runs, methods/report export |

## Generated skeletons

Inside an existing project, generate a new file:

```bash
rlab init new experiment learning_rate_sweep
rlab init new benchmark throughput
rlab init new workflow preprocessing
rlab init new data-pipeline clean_corpus
rlab init new external-adapter official_eval
rlab init new causal-experiment treatment_effect
```

Shortcuts:

```bash
rlab init experiment ablation_v1
rlab init benchmark latency
rlab init workflow train_pipeline
rlab init external-adapter external_eval
```

## What templates do not do

Templates do not hide framework magic. They write ordinary Python modules that you can edit. The only requirement is that modules containing decorators must be listed under `[modules].load` in `lab.toml`.

## Recommended workflow after generation

```bash
rlab doctor
rlab modules list
rlab discover
rlab run experiments/000_smoke.py
```

Then replace the generated components, benchmarks, and experiments with your real research code.
