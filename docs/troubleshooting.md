# Troubleshooting

## `rlab discover` finds nothing

Check module configuration:

```bash
rlab config show
rlab modules list
rlab modules doctor
```

For zero-config projects, ensure you have an importable module such as:

```text
experiments/__init__.py
experiments/sweep.py
```

## Python import fails

Run:

```bash
python -m rlab._runner
rlab modules doctor
```

Common causes:

- module is not listed in config;
- missing `__init__.py`;
- virtualenv mismatch;
- import-time exception in user code;
- package is not installed in the active environment.

## Strict mode rejects a declaration

Strict mode rejects unstable declarations such as lambdas, notebook-only functions, nested non-importable functions, and missing source files.

Use a top-level function/class in an importable module:

```python
@lab.experiment("sweep")
def sweep(ctx):
    return {"ok": True}
```

## Runs are not appearing

Check the effective run path:

```bash
rlab config show
```

Default path:

```text
.rlab/runs
```

## Artifact promotion fails

Common causes:

- source path does not exist;
- path is outside the project root and policy rejects it;
- version is missing in strict mode;
- artifact reference is malformed.

Use:

```bash
rlab artifact promote outputs/model.pt --as model:small --version 1
```

## `python -m rlab` differs from `rlab`

Both should route to the same Rust-owned command implementation. If behavior differs, the installed console script or Python package is inconsistent. Reinstall the package in the active environment.
