# rlab

`rlab` is a Rust-first, local-first research runtime packaged as a normal Python dependency.

Rust owns durable state, validation, registry semantics, run lifecycle, artifacts, reproducibility metadata, schema versions, CLI behavior, and stable JSON output. Python hosts decorators, importlib loading, and user callable execution.

## Zero-config example

```python
import rlab

lab = rlab.Project()

@lab.experiment("sweep")
def sweep(ctx):
    ctx.log_metric("loss", 0.2)
    return {"ok": True}
```

```bash
uv run rlab discover
uv run rlab run experiment:sweep
uv run rlab runs list
```
