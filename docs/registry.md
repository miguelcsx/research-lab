# Declarations and registry

The registry is the discovered catalog of project declarations.

Python decorators create declarative records. Rust validates those records and detects conflicts.

## Durable registry record

A durable record looks like this:

```json
{
  "schema_version": 1,
  "kind": "experiment",
  "name": "sweep",
  "version": "1",
  "module": "experiments.sweep",
  "qualname": "sweep",
  "source": "experiments/sweep.py",
  "tags": [],
  "description": "Learning rate sweep.",
  "metadata": {
    "question": "How does learning rate affect loss?"
  }
}
```

The durable registry never stores Python object IDs.

## Identity

Registry identity is:

```text
(kind, name)
```

A duplicate `(kind, name)` is an error unless the workflow composition rules explicitly allow multiple step declarations for the same workflow.

## Names

Names may contain:

```text
letters, digits, ., _, -, :
```

Names may not contain whitespace.

Recommended examples:

```text
project.byte
compiler.llvm_o3
babylm.clean_v1
solver.energy_error
```

Avoid:

```text
test
new
final
best
tmp
```

## Cache

Discovery can be cached at:

```text
.rlab/cache/registry.json
```

The cache is invalidated by:

- `rlab` version;
- config hash;
- module list;
- source file hashes or mtimes;
- Python executable and version;
- strict-mode policy hash.

The cache is an optimization only. Fresh discovery remains the source of truth.
