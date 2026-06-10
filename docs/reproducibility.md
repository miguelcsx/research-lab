# Reproducibility

`rlab` captures best-effort reproducibility metadata by default.

Captured files may include:

```text
reproducibility/command.txt
reproducibility/git.json
reproducibility/git.diff
reproducibility/env.json
reproducibility/lockfile
reproducibility/pyproject.toml
reproducibility/uv.lock
reproducibility/lab.toml
```

## Configuration

```toml
[reproducibility]
capture_git = true
capture_diff = true
capture_env = true
require_clean_git = false
require_lockfile = false
env_allowlist = []
```

## Strict reproducibility

Strict mode can require:

- clean Git worktree;
- dependency lockfile;
- importable declarations;
- source-backed callables;
- stable registry metadata.

```bash
rlab run experiment:sweep --strict
rlab validate --strict
rlab doctor --strict
```

## Limits

A captured run is only as reproducible as its dependencies. Reproduction can fail if:

- remote data changed;
- external APIs changed;
- GPU kernels are nondeterministic;
- OS/driver versions differ;
- untracked local files were used;
- secrets or environment variables were intentionally not captured.
