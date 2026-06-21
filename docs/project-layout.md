# Project layout and zero-config behavior

`rlab` works without a generated project. For simple use, install the package and create an `experiments` module.

## Zero-config layout

```text
project/
├── pyproject.toml
└── experiments/
    ├── __init__.py
    └── sweep.py
```

By default, runtime data goes under `.rlab`:

```text
project/
└── .rlab/
    ├── runs/
    ├── artifacts/
    └── cache/
```

## Explicit project layout

`rlab init` creates an explicit research project:

```text
project/
├── lab.toml
├── pyproject.toml
├── experiments/
├── workflows/
├── benchmarks/
├── evaluations/
└── .rlab/
    ├── runs/
    ├── artifacts/
    └── cache/
```

## Module discovery

Module loading is conservative.

`rlab` checks, in order:

1. `[python].modules` in `lab.toml`;
2. `[tool.rlab].modules` in `pyproject.toml`;
3. safe conventional modules such as `experiments`, `workflows`, `benchmarks`, and `evaluations`.

`rlab` does not recursively import every Python file in a project by default. This avoids slow startup and accidental side effects.

## Recommended `.gitignore`

```gitignore
.rlab/
.venv/
__pycache__/
*.pyc
```

Commit source files, `lab.toml` when used, and small manifests. Do not commit ordinary run directories unless intentionally frozen for a paper or release.
