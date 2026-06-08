# rlab documentation

`rlab` is a local-first research runtime. It helps a researcher or research team define experiments, benchmarks, evaluations, data pipelines, workflows, artifacts, and reproducibility metadata using ordinary Python code.

This documentation is written for someone who wants to use the library, not just read the source. Start with the quickstart, then read the domain guides that match your project.

## What rlab is

`rlab` is a Python library and CLI for reproducible research operations:

- define reusable components with decorators;
- define experiments as typed Python objects;
- run benchmarks and evaluation suites;
- build and validate datasets;
- record metrics, parameters, notes, logs, figures, tables, artifacts, and reports;
- capture environment and Git metadata;
- compare, freeze, reproduce, and hand off runs.

The core idea is simple: your research code remains normal Python, while `rlab` provides the runtime conventions around it.

## What rlab is not

`rlab` is not an AI agent, orchestration agent, notebook manager, cloud platform, training framework, or model-serving system. It does not decide what to run. A human, CLI, shell script, CI workflow, or external agent can call `rlab`, but `rlab` itself stays deterministic and local-first.

## Recommended reading order

1. [Getting started](getting-started/quickstart.md)
2. [Core mental model](concepts/mental-model.md)
3. [Project structure](getting-started/project-structure.md)
4. [Configuration](reference/configuration.md)
5. [Components and registry](guides/components-and-registry.md)
6. [Experiments](guides/experiments.md)
7. [Runs and results](guides/runs-and-results.md)
8. [Data pipelines](guides/data-pipelines.md)
9. [Benchmarks and evaluations](guides/benchmarks-and-evaluations.md)
10. [Reproducibility](guides/reproducibility.md)
11. [CLI reference](reference/cli.md)

## Documentation map

| Area | Documents |
|---|---|
| Getting started | `getting-started/quickstart.md`, `getting-started/project-structure.md`, `getting-started/templates.md` |
| Core concepts | `concepts/mental-model.md`, `concepts/references.md`, `concepts/runs-artifacts-lineage.md` |
| Guides | Components, experiments, data, benchmarks, evaluations, workflows, external commands, reproducibility, governance |
| Reference | CLI, configuration, decorators, public API, generated file layout |
| Operations | CI, reports, freezing, handoff, troubleshooting |
| Examples | AI project, data project, simulation/systems project |

## Minimal example

```python
import rlab

@rlab.component("tokenizer", "demo.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()

@rlab.benchmark("demo.token_count", target="tokenizer")
def token_count(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    return {"tokens": float(len(target.encode("research")))}
```

Run it:

```bash
rlab bench tokenizer:demo.byte demo.token_count
```

## Design principles

`rlab` is built around five constraints:

1. **Local-first:** no cloud service is required.
2. **Declarative user code:** researchers declare what exists; commands execute it.
3. **Typed records:** configuration, manifests, results, and run metadata are Pydantic models.
4. **Reproducible outputs:** every run produces a structured directory.
5. **Extensible by normal Python:** projects extend `rlab` through modules and decorators, not through a plugin marketplace.
