Packaging smoke commands for a Rust-enabled environment:

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --workspace
python -m maturin build
uv run rlab --help
uv run python -m rlab --help
```
