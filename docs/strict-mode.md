# Strict production mode

Strict mode is for CI, paper workflows, and production-grade reproducibility.

It is not enabled by default for casual local experimentation.

## Enable strict mode

```bash
rlab discover --strict
rlab run experiment:sweep --strict
rlab validate --strict
```

Or configure:

```toml
[production]
strict = true
allow_lambdas = false
allow_nested_functions = false
allow_notebook_sources = false
require_versions = true
require_clean_git = true
require_lockfile = true
```

## Strict mode rejects

- callables without source files;
- lambdas as registered production targets;
- non-importable nested functions;
- notebook-only declarations;
- duplicate registry names;
- non-serializable parameters;
- unversioned artifacts;
- missing schema versions;
- sources outside project root;
- dirty Git worktree when policy requires clean state;
- missing lockfile when policy requires it;
- stale registry cache;
- unstable declaration metadata.

## Relaxed mode

Relaxed mode warns for many production issues but still rejects correctness errors such as invalid registry names and duplicate declarations.
