# Reproducibility

`rlab` captures enough metadata to inspect and often replay a run.

## What is captured

Depending on `lab.toml`, each run can capture:

| File | Meaning |
|---|---|
| `reproducibility/command.txt` | Command used by the session |
| `reproducibility/git.json` | Commit, branch, remote, dirty state |
| `reproducibility/git.diff` | Working tree diff |
| `reproducibility/env.json` | Python, executable, platform, selected env vars, packages |
| `reproducibility/lockfile` | Marker that dependency files were copied |
| `reproducibility/pyproject.toml` | Project dependency file |
| `reproducibility/uv.lock` | Lockfile when present |
| `reproducibility/lab.toml` | Effective project config source |

## Configuration

```toml
[reproducibility]
capture_git = true
capture_diff = true
capture_env = true
capture_packages = true
capture_lockfile = true
capture_command = true
capture_data_manifests = true
allow_dirty = false
env_allowlist = []
```

## Reproduction plan

Show what command would be replayed:

```bash
rlab reproduce runs/<run-id> --dry-run
```

## Reproduce a run

```bash
rlab reproduce runs/<run-id>
```

For strict checks:

```bash
rlab reproduce runs/<run-id> --strict
```

Strict mode checks:

- current environment matches recorded environment, unless `--use-current-env`;
- recorded/current Git state is clean, unless `--allow-dirty`;
- current commit matches recorded commit.

## Checkout reproduction

```bash
rlab reproduce runs/<run-id> --checkout
```

This uses the recorded Git remote and commit to check out the repository into the reproduction cache, then builds a runtime there.

## Container reproduction

```bash
rlab reproduce runs/<run-id> --container
```

This requires:

```toml
[launcher]
docker_image = "your-image"
```

## Reproducibility limitations

A captured run is only as reproducible as its dependencies. Reproduction may fail when:

- remote data changed;
- external APIs changed;
- GPU kernels are nondeterministic;
- OS or driver versions differ;
- external repositories disappear;
- environment variables or secrets were not captured;
- a run depended on untracked local files.

## Good practices

- Use `uv.lock`.
- Commit source code before expensive runs.
- Store input datasets as manifests with checksums.
- Promote important artifacts.
- Avoid reading uncontrolled paths.
- Avoid random seeds hidden in libraries.
- Record explicit seeds in experiments.
- Use `rlab freeze` for paper-critical runs.
