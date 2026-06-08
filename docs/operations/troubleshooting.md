# Troubleshooting

This page lists common failures and how to debug them.

## `No lab.toml found`

Run commands from a project root or pass `--root`:

```bash
rlab --root /path/to/project doctor
```

Create a project if needed:

```bash
rlab init project my-project
```

## Module not found

Check `lab.toml`:

```toml
[modules]
load = ["components.models"]
```

The module must be importable from the project root:

```text
components/models.py
components/__init__.py
```

Debug:

```bash
rlab modules list
rlab modules doctor
```

## Registry entry not found

Example:

```text
Unknown benchmark 'project.latency'
```

Check:

```bash
rlab discover
rlab discover benchmarks
```

Causes:

- module not listed in `lab.toml`;
- decorator name is different;
- import failed before decorator ran;
- registry kind is wrong;
- benchmark target kind does not match component reference.

## Registry conflict

Two different objects registered the same kind/name. Rename one, remove duplicate imports, or split modules.

## Benchmark target mismatch

If a benchmark targets `tokenizer`, run it against:

```bash
rlab bench tokenizer:project.byte project.tokenizer.length
```

not:

```bash
rlab bench model:project.constant project.tokenizer.length
```

## Bad reference

References require a scheme:

```text
tokenizer:project.byte
artifact:dataset/project.clean@candidate
manifest:clean_v1
```

Invalid:

```text
project.byte
artifact:name
```

## Reproduction strict mode fails

Common causes:

- current environment differs from recorded environment;
- current Git commit differs;
- recorded or current worktree is dirty.

Use:

```bash
rlab reproduce runs/<run-id> --dry-run
rlab reproduce runs/<run-id> --strict --use-current-env
rlab reproduce runs/<run-id> --strict --allow-dirty
```

Only relax strictness when you understand the tradeoff.

## Dataset checksum fails

A manifest output changed after manifest creation. Rebuild the dataset or restore the original file.

```bash
rlab data build dataset:project.clean
```

Do not edit materialized dataset files after manifest creation.

## External command fails

Inspect:

```text
runs/<run-id>/external/<step>.stdout
runs/<run-id>/external/<step>.stderr
runs/<run-id>/logs/error.txt
```

Check command paths and working directory.

## Docker launcher fails

Set:

```toml
[launcher]
docker_image = "your-image"
```

Confirm Docker is installed and can run:

```bash
docker run --rm your-image python --version
```

## Search returns nothing

The search index is rebuilt from `runs/`, `manifests/`, and `artifacts/`. Make sure run directories contain `run.yaml`.

```bash
rlab search "term"
```

## Runs list is empty but run folders exist

The run index is stored in `.rlab/runs.db`. Some runs may predate the index or were copied manually. Use `compare runs/` or inspect folders directly. Re-running or rebuilding index-related commands may repopulate metadata for future runs.

## `uv lock` fails during project init

`rlab init project` calls `uv lock` after writing the template. If it fails, the project files may still exist. Enter the project and run:

```bash
uv lock
uv sync
rlab doctor
```
