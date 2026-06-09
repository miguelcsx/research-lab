# Components and registry

Components are reusable pieces of project code: models, tokenizers, solvers, compilers, datasets, feature extractors, proof checkers, or any object your benchmarks and workflows need.

## Register a component

```python
import rlab

@rlab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()
```

The reference is:

```text
tokenizer:project.byte
```

## Component kinds

The first argument to `@rlab.component` is the kind:

```python
@rlab.component("model", "baseline.constant")
class ConstantModel: ...

@rlab.component("solver", "fdtd.yee")
class YeeSolver: ...

@rlab.component("compiler", "clang.o3")
class ClangO3: ...
```

Kinds are open-ended. A benchmark declares which kind it targets:

```python
@rlab.benchmark("solver.energy_error", target="solver")
def energy_error(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    ...
```

`rlab` checks that a benchmark targeting `solver` is not accidentally run against a `tokenizer`.

## Build a component

Internally, the runtime uses:

```python
from rlab.components import Tokenizer, build_component

component = build_component(runtime.registry, "tokenizer:project.byte")
if not isinstance(component, Tokenizer):
    raise TypeError("component must implement Tokenizer")
```

If the registered value is a class, `rlab` instantiates it. If it is already an object or factory value, it returns it.
Pass `expected=ConcreteComponent` when a concrete component class is available;
`rlab` then validates the value and preserves that type in the return value.

## Load modules

Only modules listed in `lab.toml` are imported automatically.

```toml
[modules]
load = [
  "components.tokenizers",
  "components.models",
  "benchmarks.custom",
]
```

Check loading:

```bash
rlab modules list
rlab modules doctor
rlab discover
```

## Registry records

A registry record stores:

| Field | Meaning |
|---|---|
| `kind` | component, benchmark, suite, experiment, dataset, etc. |
| `name` | unique registry name |
| `value` | Python object/class/function |
| `version` | semantic version string |
| `target_kind` | component kind required by benchmark, if any |
| `module` | Python module |
| `qualname` | qualified object name |
| `source` | source file path |
| `description` | first line of docstring |
| `tags` | optional tags |
| `package` | usually `project` |

## Naming rules

Registry names may contain letters, numbers, `.`, `_`, `-`, and `:`. They may not contain whitespace.

Good:

```text
project.tokenizer.length
babylm.clean_v1
fdtd.energy_error
compiler.llvm_o3
```

Bad:

```text
my benchmark
new best thing
```

## Avoiding conflicts

Registry conflicts happen when two different objects register the same `(kind, name)` pair. Fix by renaming one object or removing duplicated module imports.

## Recommended module style

Keep modules declarative:

```python
import rlab

@rlab.component("model", "project.small")
class SmallModel:
    ...

@rlab.benchmark("project.accuracy", target="model")
def accuracy(model: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    ...
```

Avoid side effects at import time. Decorators are expected. Expensive downloads, training, external commands, and file writes should happen inside benchmarks, workflows, or experiments, not at module import.
