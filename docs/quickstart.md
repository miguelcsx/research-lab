# Quickstart

This guide shows the minimum useful `rlab` project. No `lab.toml` is required.

## 1. Add rlab

```bash
uv add rlab
```

For internal Git installation:

```toml
[project]
dependencies = ["rlab"]

[tool.uv.sources]
rlab = { git = "ssh://git@github.com/miguelcsx/research-lab.git", rev = "<pinned-commit>" }
```

## 2. Create an experiment module

```bash
mkdir -p experiments
printf '' > experiments/__init__.py
```

Create `experiments/sweep.py`:

```python
import rlab

lab = rlab.Project()

@lab.experiment("sweep")
def sweep(ctx):
    ctx.log_metric("loss", 0.2)
    return {"ok": True}
```

## 3. Discover declarations

```bash
uv run rlab discover
```

`rlab` will infer the project root and import conventional modules such as `experiments`.

## 4. Run the experiment

```bash
uv run rlab run experiment:sweep
```

This creates a run under `.rlab/runs` by default.

## 5. Inspect runs

```bash
uv run rlab runs list
uv run rlab runs show <run-id>
```

Machine-readable output is available everywhere:

```bash
uv run rlab runs list --json
```

## 6. Make config explicit, when needed

```bash
uv run rlab init
```

Generated `lab.toml`:

```toml
schema_version = 1

[project]
name = "my-project"

[paths]
runs = ".rlab/runs"
artifacts = ".rlab/artifacts"
cache = ".rlab/cache"

[python]
modules = ["experiments"]

[production]
strict = false
```
