# Architecture

`rlab` is a Rust-first system distributed as a normal Python package.

## Crates

```text
crates/
├── rlab-core
├── rlab-cli
└── rlab-py
```

## Python package

```text
python/rlab/
├── __init__.py
├── __main__.py
├── _runner.py
├── _loader.py
├── _decorators.py
├── _rlab.pyi
└── py.typed
```

## Ownership boundaries

Rust owns:

- config and validation;
- registry semantics;
- run lifecycle;
- artifacts;
- reproducibility;
- migrations;
- JSON output;
- diagnostics;
- file locking;
- schema versions;
- CLI orchestration.
- dataset execution loops, decisions, audit artifacts, and sink dispatch;
- external command execution.

Python owns:

- decorators;
- importlib module loading;
- callable resolution;
- the user-callable boundary;
- Pythonic facade APIs;
- type stubs;
- Python runner process.

## Runtime flow

1. Rust CLI receives the command.
2. Rust core discovers root and loads config.
3. Rust validates command request.
4. Rust creates or opens run state when needed.
5. Rust starts Python runner only if Python code is required.
6. Python imports project modules and executes user callables.
7. Python emits structured protocol events.
8. Rust validates events and persists durable state.
9. Rust finalizes the run.
10. Rust renders human output or stable JSON.

## Why this boundary exists

Python is excellent for research declarations and user-code ergonomics. Rust is better for durable state, validation, filesystem safety, stable protocols, and high-performance local tooling.

The boundary keeps the system reproducible and maintainable while preserving a natural Python API.
