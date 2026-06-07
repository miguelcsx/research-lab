# rlab

> **Declarative, local-first runtime for research experiments**

`rlab` is a comprehensive framework designed for researchers and ML engineers who need reproducible, auditable, and portable research workflows. Define your research once using Python decorators and configuration, then run it anywhere with full traceability.

## ✨ Key Capabilities

| | |
|---|---|
| ⚡ **Experiments** | Declarative experiment execution with built-in tracking |
| 📊 **Benchmarks** | Atomic performance measurements across models |
| 🔬 **Evaluations** | Structured evaluation suites and tasks |
| 💾 **Data Pipelines** | Versioned, reproducible data processing |
| 🔗 **Components** | Reusable, discoverable model and tool components |
| 📦 **Artifacts** | Version and manage experiment outputs |

## 🚀 Get Running in 30 Seconds

### 1. Install

```bash
uv sync
uv run rlab --help
```

### 2. Create a Project

```bash
uv run rlab init project my-research
cd my-research
uv run rlab doctor
```

### 3. Run an Experiment

```bash
uv run rlab run experiments/000_smoke.py
```

## 🛠️ Core Commands

```bash
# Discover all registered components and experiments
rlab discover

# Run targeted performance measurements
rlab bench tokenizer:project.byte project.tokenizer.length

# Execute evaluation suites with model targets
rlab eval project.quick --model model:project.constant

# Build and manage versioned datasets
rlab data build dataset:project.tiny

# Execute a complete research experiment
rlab run experiments/000_smoke.py

# Compare results or reproduce exact runs
rlab compare runs/
rlab reproduce runs/<run-id> --strict

# Manage artifacts and jobs
rlab artifacts list
rlab jobs list
```

## 💡 Why rlab?

<table>
  <tr>
    <td width="50%">
      <h4>🏠 Local First</h4>
      <p>No cloud required. All computation happens on your machine. Full control, no vendor lock-in, complete privacy.</p>
    </td>
    <td width="50%">
      <h4>📝 Declarative</h4>
      <p>Use Python decorators to declare experiments, benchmarks, and components. Focus on research logic, not infrastructure.</p>
    </td>
  </tr>
  <tr>
    <td>
      <h4>🔄 Reproducible</h4>
      <p>Every run captures code state, dependencies, environment variables, and outputs. Reproduce any experiment exactly.</p>
    </td>
    <td>
      <h4>📊 Observable</h4>
      <p>Automatic tracking of metrics, results, artifacts, and logs. Built-in reporting and run comparison tools.</p>
    </td>
  </tr>
  <tr>
    <td>
      <h4>🔌 Pluggable</h4>
      <p>Extend with plugins via the <code>rlab.plugins</code> entry-point. Reuse components across projects.</p>
    </td>
    <td>
      <h4>⚙️ Strict</h4>
      <p>Full type hints, comprehensive testing (95%+ coverage), linting, and mypy strictness built in.</p>
    </td>
  </tr>
</table>

## 📝 Example: A Simple Benchmark

Define a component and benchmark it in just a few lines:

```python
import rlab

# Define a component
@rlab.component("tokenizer", "tiny.bytes")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

# Benchmark it
@rlab.benchmark("tiny.length", target="tokenizer")
def length(target: object, context: rlab.BenchmarkContext) -> dict[str, float]:
    return {"tokens": float(len(target.encode("research")))}
```

That's it. Now you can run:
```bash
rlab bench tokenizer:project.byte project.tokenizer.length
```

## 📦 What Each Run Produces

Every completed experiment generates a comprehensive audit trail:

- `run.yaml` — Configuration and metadata
- `metrics.jsonl` — Streaming metric events  
- `results.json` — Structured final results
- `report.md` — Human-readable summary
- `git.json` — Git state (commit, branch, status)
- `env.json` — Environment variables
- `logs/` — All captured output
- `artifacts/` — Models, datasets, checkpoints
- Lockfiles from your project dependencies

Perfect for debugging, auditing, and reproducing experiments months later.

## 🏗️ Architecture

**Plugin-based registry system:** Projects and installed packages register experiments, benchmarks, evaluations, datasets, and components through decorators. The registry is immutable, typed, and queryable via the CLI or Python API.

### Core Modules

- **experiments** — Experiment definition and execution
- **benchmarks** — Performance measurement and aggregation
- **evaluations** — Evaluation suites and tasks
- **data** — Data pipelines, ablations, and versioning
- **components** — Model and tool component management
- **artifacts** — Artifact tracking and storage
- **runs** — Run manifest and reproducibility tracking
- **tracking** — Metrics and result collection
- **reporting** — Report generation and run comparison
- **cli** — Type-safe Typer CLI with Rich output

## ✅ Quality Assurance

```bash
# Type checking
uv run mypy rlab tests

# Linting
uv run ruff check rlab tests

# Format checking
uv run ruff format --check rlab tests

# Tests with coverage enforcement (95%+ required)
uv run pytest
```

All code is strictly typed, comprehensively tested, and linted.

## 🎯 Getting Started

1. Check out the `examples/` directory for a minimal working project
2. Read through the `docs/` folder for detailed guides
3. Run `rlab doctor` after project init to verify your setup
4. Start building: define components, create benchmarks, run experiments

## 📋 Requirements

- **Python:** 3.11+
- **Core Dependencies:**
  - Pydantic 2.8+
  - PyYAML 6.0+
  - Rich 13.7+
  - Typer 0.16+
- **Optional:** Hydra for advanced config, HuggingFace Transformers for NLP work

## 🎓 How It Works

Projects register components, benchmarks, suites, datasets, and experiments through decorators:

```python
@rlab.component("kind", "name")
@rlab.benchmark("name", target="component_kind")
@rlab.eval("suite_name", target="model_kind")
@rlab.data("dataset_name")
```

Installed packages can contribute the same declarations through the `rlab.plugins` entry-point group, making it easy to share reusable research components across your team or the community.

## 💭 Philosophy

`rlab` is built for researchers who want reproducible, auditable research that runs on their hardware. **No APIs. No cloud bills. No dependency on external services.** Pure, portable Python.

Whether you're benchmarking tokenizers, evaluating language models, or building data pipelines, rlab keeps your research local, transparent, and reproducible.

---

**rlab** — Version 0.1.0 | Declarative, local-first research runtime
