# Packaging and distribution

`rlab` should feel like a normal Python dependency.

## Wheel contents

The wheel includes:

- `rlab._rlab` compiled PyO3 extension;
- thin Python facade;
- Python runner;
- type stubs and `py.typed`;
- templates;
- console command `rlab`;
- `python -m rlab` fallback.

## CLI entrypoint

The console script calls into the Rust-owned CLI through the PyO3 extension.

The Python entrypoint must not reimplement command behavior.

## Source installs

Private Git installs are useful during internal development:

```toml
[tool.uv.sources]
rlab = { git = "ssh://git@github.com/miguelcsx/research-lab.git", rev = "<pinned-commit>" }
```

Source installs may require Rust and maturin.

## Production installs

Production users should consume prebuilt wheels from a private or public index.

Prebuilt wheels should target supported Linux, macOS, and Windows platforms where practical.

## Recommended release checks

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
uv run maturin build
uv run python -c "import rlab; print(rlab.__all__)"
```
