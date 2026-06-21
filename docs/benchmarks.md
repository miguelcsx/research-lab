# Benchmarks

A benchmark is a runnable target for repeatable measurement. The benchmark
decides what to load, compare, or measure from runtime params.

## Define a Benchmark

```python
import rlab

lab = rlab.Project()

@lab.benchmark("project.tokenizer.length")
def length(ctx):
    text = ctx.param("text", "research")
    tokens = list(str(text).encode())
    value = float(len(tokens))
    ctx.log_metric("tokens", value)
    return {"tokens": value}
```

Run:

```bash
rlab run benchmark:project.tokenizer.length --set text=research
```

## Targets

If a benchmark needs a model, tokenizer, solver, corpus, or external system,
encode that lookup in project code or pass an artifact/run reference through
params. `rlab` stores the run evidence; it does not own the scientific object.
