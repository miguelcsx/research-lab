# CI and quality workflows

`rlab` includes commands designed for local CI and project health checks.

## Smoke check

```bash
rlab ci smoke
```

The smoke check validates:

1. config loads;
2. modules import;
3. registry entries are discoverable.

Use it in CI:

```yaml
- name: rlab smoke
  run: uv run rlab ci smoke
```

## Reproducibility check

```bash
rlab ci reproducibility-check
```

This checks recent runs for dirty Git state and missing lockfile markers.

## Regression check

```bash
rlab ci compare \
  --baseline <baseline-run-id> \
  --candidate <candidate-run-id> \
  --metric accuracy \
  --threshold 0.01
```

The command fails if the absolute metric delta exceeds the threshold.

## Doctor

```bash
rlab doctor
```

Checks:

- `lab.toml` exists;
- `pyproject.toml` exists;
- runtime paths are writable;
- `git` and `uv` exist;
- project is a Git repo;
- configured modules load;
- project validation passes.

## Lint

```bash
rlab lint
```

Checks project-specific research conventions:

- experiment definitions should include questions and hypotheses;
- run directories should contain manifests;
- large untracked files are reported;
- declared modules should exist.

## Recommended CI pipeline

```bash
uv sync --all-extras
uv run ruff check rlab tests
uv run ruff format --check rlab tests
uv run mypy rlab tests
uv run pytest
uv run rlab --root examples/project ci smoke
```

For a research project using `rlab`:

```bash
uv sync
uv run rlab doctor
uv run rlab modules doctor
uv run rlab discover
uv run rlab ci smoke
uv run rlab lint
```

## Project-level testing

Use `rlab.testing` helpers:

```python
from rlab.testing import assert_metric_exists, assert_valid_run_dir

assert_valid_run_dir(run_path)
assert_metric_exists(run_path, "accuracy")
```

## When CI should fail

Fail CI when:

- modules cannot import;
- config is invalid;
- required registry entries are missing;
- critical metrics regress beyond threshold;
- selected runs are stale;
- reproduction metadata is incomplete for publishable runs.

Do not fail CI for exploratory negative results. Record them in the journal instead.
