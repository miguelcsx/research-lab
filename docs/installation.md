# Installation

`rlab` is distributed as a normal Python package even though the runtime is Rust-first.

Users should not need to understand Rust to install or use it.

## Recommended production install

For production users, install a prebuilt wheel from a private or public package index:

```toml
[project]
dependencies = ["rlab==0.1.0"]
```

With a private index:

```toml
[project]
dependencies = ["rlab==0.1.0"]

[[tool.uv.index]]
name = "company"
url = "https://packages.example.internal/simple"
```

This is the preferred distribution path because users do not need a Rust toolchain.

## Private Git install during development

During internal development, `rlab` may be installed directly from the private Git repository:

```toml
[project]
dependencies = ["rlab"]

[tool.uv.sources]
rlab = { git = "ssh://git@github.com/miguelcsx/research-lab.git", rev = "<pinned-commit>" }
```

Always pin by `rev` or release tag. Do not use a floating branch for reproducible research projects.

A source install may require:

- Rust toolchain;
- maturin;
- platform C/Rust build dependencies;
- access to the private repository.

This is acceptable for contributors and internal teams, but prebuilt wheels are preferred for ordinary users.

## What the wheel contains

The Python wheel includes:

- `rlab._rlab`, the compiled PyO3 extension;
- the thin Python facade;
- `rlab._runner`, the Python host process used by Rust for Python code;
- type stubs and `py.typed`;
- templates used by `rlab init`;
- the `rlab` console command;
- `python -m rlab` fallback entrypoint.

## Verify installation

```bash
uv run rlab --help
uv run python -m rlab --help
```

If both commands print help, the package and CLI entrypoints are available.

## Build from source

Contributors can build locally with maturin:

```bash
uv sync
uv run maturin develop
uv run rlab --help
```

The Rust workspace can also be checked directly:

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
```
