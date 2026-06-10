# Benchmarks

A benchmark measures one target component.

## Component and benchmark

```python
import rlab

lab = rlab.Project()

@lab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

@lab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target, ctx):
    return {"tokens": float(len(target.encode("research")))}
```

Run:

```bash
rlab benchmark tokenizer:project.byte project.tokenizer.length
```

## Target references

A target reference has the shape:

```text
<kind>:<name>
```

Example:

```text
tokenizer:project.byte
model:project.constant
solver:fdtd_v1
```

Rust validates that the benchmark target kind matches the requested component kind.
