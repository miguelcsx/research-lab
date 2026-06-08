# Quickstart

This page takes you from a clean repository to a running `rlab` experiment.

## Requirements

`rlab` requires Python 3.11 or newer. The repository is designed to be used with `uv`, but the Python package itself is ordinary Python.

Core dependencies:

```text
pydantic
pyyaml
rich
typer
```

Optional dependency groups are declared in `pyproject.toml`, including `hydra`, `dev`, and `hf`.

## Install from the repository

From the repository root:

```bash
uv sync
uv run rlab --help
```

You can also run the package module directly:

```bash
uv run python -m rlab --help
```

## Create a new research project

```bash
uv run rlab init project my-research --template ai
cd my-research
uv run rlab doctor
```

The generated project includes:

```text
my-research/
├── lab.toml
├── pyproject.toml
├── experiments/
│   └── 000_smoke.py
├── components/
├── benchmarks/
├── evaluations/
├── data_pipelines/
├── manifests/
├── runs/
├── artifacts/
└── reports/
```

## Run the generated smoke experiment

```bash
uv run rlab run experiments/000_smoke.py
```

The command creates a new directory under `runs/`. The directory contains metadata, metrics, environment capture, results, and a Markdown report.

Inspect it:

```bash
uv run rlab runs list
uv run rlab runs show <run-id>
uv run rlab report run runs/<run-id>
```

## Run a benchmark directly

The generated `ai` template registers a byte tokenizer and a simple token-count benchmark.

```bash
uv run rlab bench tokenizer:project.byte project.tokenizer.length
```

## Run an evaluation suite

```bash
uv run rlab eval project.quick --model model:project.constant
```

## Build a dataset variant

```bash
uv run rlab data build dataset:project.tiny
```

Then inspect the generated dataset manifest:

```bash
uv run rlab data profile runs/<data-run-id>/artifacts/dataset/manifest.yaml
uv run rlab data sample runs/<data-run-id>/artifacts/dataset/manifest.yaml --n 1
```

## Discover registered objects

`rlab` loads modules from `lab.toml`. Decorators in those modules register components, benchmarks, suites, datasets, workflows, and experiments.

```bash
uv run rlab discover
uv run rlab discover benchmarks
uv run rlab modules list
```

## Common first workflow

```bash
uv run rlab doctor
uv run rlab discover
uv run rlab run experiments/000_smoke.py
uv run rlab runs list
uv run rlab compare runs/
uv run rlab reproduce runs/<run-id> --dry-run
```

## When something fails

Start with:

```bash
uv run rlab doctor
uv run rlab modules doctor
uv run rlab lint
```

Then open the run directory and inspect:

```text
logs/error.txt
run.yaml
params.json
metrics.jsonl
results.json
reproducibility/
```
