# rlab documentation

`rlab` is a local-first research runtime. It lets a team declare research objects in ordinary Python, execute them through a Rust-owned runtime, and keep durable run records that can be inspected, compared, reproduced, frozen, and handed off.

The most important rule is:

> Rust owns the product runtime. Python hosts user code.

This means users get Python-native decorators and callable execution, while the CLI, state machine, validation, artifacts, manifests, reproducibility, migrations, and stable JSON output are Rust-owned.

## Start here

1. [Install rlab](installation.md)
2. [Quickstart](quickstart.md)
3. [Core concepts](concepts.md)
4. [Configuration](configuration.md)
5. [CLI reference](cli.md)
6. [Python API](python-api.md)

## Topic guides

- [Project layout and zero-config behavior](project-layout.md)
- [Declarations and registry](registry.md)
- [Experiments](experiments.md)
- [Workflows](workflows.md)
- [Benchmarks](benchmarks.md)
- [Evaluations](evaluations.md)
- [Data pipelines](data.md)
- [Runs and runtime context](runs.md)
- [Artifacts and lineage](artifacts.md)
- [Reproducibility](reproducibility.md)
- [Journal, notes, baselines, and search](journal-search-baselines.md)
- [Strict production mode](strict-mode.md)
- [Architecture](architecture.md)
- [Python runner protocol](runner-protocol.md)
- [Packaging and distribution](packaging.md)
- [Troubleshooting](troubleshooting.md)

## Guarantees

`rlab` is designed around these guarantees:

- local-first operation;
- zero-config first use;
- stable machine-readable CLI output with `--json`;
- schema versions in durable files;
- append-only event logs where appropriate;
- atomic writes for manifests and summaries;
- explicit run state transitions;
- no durable registry state based on process-local Python callable IDs;
- strict production mode for reproducible research and CI.
