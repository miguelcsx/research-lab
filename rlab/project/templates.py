import subprocess
from pathlib import Path

_LAB_TOML_BASE = """\
[project]
name = "{name}"

[modules]
load = [
{module_lines}]

[paths]
runs = "runs"
artifacts = "artifacts"
manifests = ["manifests"]
reports = "reports"
cache = ".rlab"

[tracking]
backend = "local"

[artifacts]
backend = "local"

[reproducibility]
capture_git = true
capture_env = true
capture_lockfile = true
capture_command = true
"""

_PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["{rlab_dependency}"]

[dependency-groups]
dev = ["pytest", "ruff", "mypy"]
"""

_GITIGNORE = ".venv/\n.rlab/\nruns/\nartifacts/\n"


_SMOKE_EXPERIMENT = """\
import rlab


@rlab.experiment("000_smoke")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="Does the generated project execute?",
        matrix={"target": ["tokenizer:project.byte"]},
        benchmarks=("project.tokenizer.length",),
    )
"""

_COMPONENT_STUB = """\
import rlab


@rlab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()
"""

_MODEL_STUB = """\
import rlab


@rlab.component("model", "project.constant")
class ConstantModel:
    def __call__(self, inputs: object) -> float:
        return 1.0
"""

_BENCHMARK_STUB = """\
import rlab


@rlab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target: object, ctx: rlab.BenchmarkContext) -> rlab.ResultBundle:
    tokens = target.encode("research")
    return rlab.ResultBundle(metrics=[rlab.Metric(name="tokens", value=float(len(tokens)))])
"""

_SUITE_STUB = """\
import rlab


def score(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"score": float(model(None))}


@rlab.suite("project.quick")
def quick() -> rlab.EvaluationSuite:
    return rlab.EvaluationSuite(
        tasks=(rlab.EvaluationTask(name="score", evaluator=score),),
    )
"""

_DATA_STUB = """\
import rlab


@rlab.data_source("project.tiny_source")
def source(ctx: rlab.DataContext):
    yield {"text": "research"}
    yield {"text": "lab"}


@rlab.data_transform("project.uppercase")
def uppercase(records, ctx: rlab.DataContext):
    for record in records:
        yield {**record, "text": str(record["text"]).upper()}


@rlab.data_check("project.nonempty")
def nonempty(records, ctx: rlab.DataContext):
    return {"success": any(True for _ in records), "severity": "error"}


@rlab.data_metric("project.record_count")
def record_count(records, ctx: rlab.DataContext) -> float:
    return float(sum(1 for _ in records))


@rlab.dataset_variant("project.tiny")
def tiny() -> rlab.DataPipeline:
    return rlab.DataPipeline(
        sources=("project.tiny_source",),
        transforms=("project.uppercase",),
        checks=("project.nonempty",),
        metrics=("project.record_count",),
    )
"""

_WORKFLOW_STUB = """\
import rlab


@rlab.workflow("project.main")
def main() -> rlab.Workflow:
    return rlab.Workflow(
        steps=["project.step_one"],
        description="Main project workflow",
    )
"""

_SOLVER_STUB = """\
import rlab


@rlab.component("solver", "project.basic")
class BasicSolver:
    def solve(self, inputs: object) -> dict[str, float]:
        return {"result": 1.0}
"""


_TEMPLATES: dict[str, dict[str, object]] = {
    "basic": {
        "modules": [
            '  "components.models",',
            '  "benchmarks.custom",',
        ],
        "dirs": [
            "experiments",
            "components",
            "benchmarks",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": ["components", "benchmarks"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "components/models.py": _COMPONENT_STUB,
            "benchmarks/custom.py": _BENCHMARK_STUB,
        },
    },
    "ai": {
        "modules": [
            '  "components.tokenizers",',
            '  "components.models",',
            '  "benchmarks.custom",',
            '  "evaluations.suites",',
            '  "ingest.sources",',
        ],
        "dirs": [
            "experiments",
            "components",
            "benchmarks",
            "evaluations",
            "suites",
            "ingest",
            "workflows",
            "adapters",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": [
            "components",
            "benchmarks",
            "evaluations",
            "suites",
            "ingest",
            "workflows",
            "adapters",
        ],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "components/tokenizers.py": _COMPONENT_STUB,
            "components/models.py": _MODEL_STUB,
            "benchmarks/custom.py": _BENCHMARK_STUB,
            "evaluations/suites.py": _SUITE_STUB,
            "ingest/sources.py": _DATA_STUB,
        },
    },
    "data": {
        "modules": [
            '  "ingest.sources",',
            '  "ingest.cleaning",',
            '  "benchmarks.quality",',
        ],
        "dirs": [
            "experiments",
            "ingest",
            "benchmarks",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": ["ingest", "benchmarks"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "ingest/sources.py": _DATA_STUB,
            "benchmarks/quality.py": _BENCHMARK_STUB,
        },
    },
    "simulation": {
        "modules": [
            '  "components.solvers",',
            '  "workflows.main",',
            '  "benchmarks.convergence",',
        ],
        "dirs": [
            "experiments",
            "components",
            "workflows",
            "benchmarks",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": ["components", "workflows", "benchmarks"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "components/solvers.py": _SOLVER_STUB,
            "workflows/main.py": _WORKFLOW_STUB,
            "benchmarks/convergence.py": _BENCHMARK_STUB,
        },
    },
    "lean": {
        "modules": [
            '  "adapters.lake",',
            '  "benchmarks.proofs",',
        ],
        "dirs": [
            "experiments",
            "adapters",
            "benchmarks",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": ["adapters", "benchmarks"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "benchmarks/proofs.py": _BENCHMARK_STUB,
        },
    },
    "systems": {
        "modules": [
            '  "components.compilers",',
            '  "workflows.benchmark_run",',
            '  "benchmarks.performance",',
        ],
        "dirs": [
            "experiments",
            "components",
            "workflows",
            "benchmarks",
            "adapters",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "tests",
        ],
        "packages": ["components", "workflows", "benchmarks", "adapters"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "components/compilers.py": _COMPONENT_STUB,
            "benchmarks/performance.py": _BENCHMARK_STUB,
        },
    },
    "paper": {
        "modules": [
            '  "components.models",',
            '  "benchmarks.main",',
            '  "evaluations.paper_eval",',
            '  "workflows.paper_pipeline",',
        ],
        "dirs": [
            "experiments",
            "components",
            "benchmarks",
            "evaluations",
            "workflows",
            "manifests",
            "runs",
            "artifacts",
            "reports",
            "paper",
            "tests",
        ],
        "packages": ["components", "benchmarks", "evaluations", "workflows"],
        "files": {
            "experiments/000_smoke.py": _SMOKE_EXPERIMENT,
            "components/models.py": _MODEL_STUB,
            "benchmarks/main.py": _BENCHMARK_STUB,
            "evaluations/paper_eval.py": _SUITE_STUB,
        },
    },
}


_NEW_EXPERIMENT = """\
import rlab


@rlab.experiment("{name}")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="What is the research question?",
        hypothesis="What do you expect to find?",
        matrix={{
            "param": ["value_a", "value_b"],
        }},
    )
"""

_NEW_BENCHMARK = """\
import rlab


@rlab.benchmark("{name}", target="component_kind")
def benchmark(target: object, ctx: rlab.BenchmarkContext) -> rlab.ResultBundle:
    return rlab.ResultBundle(
        metrics=[rlab.Metric(name="score", value=0.0)],
    )
"""

_NEW_WORKFLOW = """\
import rlab


@rlab.workflow("{name}")
def workflow() -> rlab.Workflow:
    return rlab.Workflow(
        steps=["step_one", "step_two"],
        description="Describe what this workflow does.",
    )
"""

_NEW_DATA_PIPELINE = """\
import rlab


@rlab.dataset_variant("{name}")
def pipeline() -> rlab.DataPipeline:
    return rlab.DataPipeline(
        sources=("source.raw",),
        transforms=("transform.clean",),
        checks=("check.schema",),
        metrics=("metric.count",),
    )
"""

_NEW_REPORT = """\
# {name} report
# Auto-generated by rlab new report {name}

import rlab


def generate(run_dir, ctx):
    \"\"\"Custom report generator for {name}.\"\"\"
    pass
"""

_NEW_ADAPTER = """\
import rlab


@rlab.adapter("{name}")
class MyAdapter(rlab.BaseAdapter):
    def command(self, ctx: rlab.AdapterContext) -> rlab.ExternalCommand:
        return rlab.ExternalCommand(
            args=("python", "-m", "evaluation_module", "--target", "{{model}}"),
        )
"""

_NEW_CAUSAL_EXPERIMENT = """\
import rlab


@rlab.experiment("{name}")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="What is the causal effect of X on Y?",
        hypothesis="X causes Y through mechanism Z.",
        matrix={{
            "treatment": ["treated", "control"],
        }},
        decision_criteria="Select treatment if effect > threshold with p < 0.05.",
        assumptions=(
            "Treatment and control are identical except for the intervention.",
            "No confounding variables.",
        ),
        threats=(
            "Limited sample size may reduce statistical power.",
        ),
    )
"""

_NEW_TEMPLATES = {
    "experiment": _NEW_EXPERIMENT,
    "benchmark": _NEW_BENCHMARK,
    "workflow": _NEW_WORKFLOW,
    "ingest": _NEW_DATA_PIPELINE,
    "report": _NEW_REPORT,
    "adapter": _NEW_ADAPTER,
    "causal-experiment": _NEW_CAUSAL_EXPERIMENT,
}


def write_project(root: Path, name: str, template: str = "ai") -> Path:
    project = root / name
    project.mkdir(parents=True, exist_ok=True)

    spec = _TEMPLATES.get(template, _TEMPLATES["ai"])
    dirs: list[str] = spec["dirs"]  # type: ignore[assignment]
    packages: list[str] = spec["packages"]  # type: ignore[assignment]
    module_lines: list[str] = spec["modules"]  # type: ignore[assignment]
    files: dict[str, str] = spec["files"]  # type: ignore[assignment]

    for directory in dirs:
        (project / directory).mkdir(parents=True, exist_ok=True)
    for package in packages:
        pkg = project / package
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("")

    (project / "lab.toml").write_text(
        _LAB_TOML_BASE.format(name=name, module_lines="\n".join(module_lines) + "\n")
    )

    source = Path(__file__).parents[2]
    dependency = (
        f"rlab @ {source.as_uri()}" if (source / "pyproject.toml").exists() else "rlab>=0.1"
    )
    (project / "pyproject.toml").write_text(
        _PYPROJECT.format(name=name, rlab_dependency=dependency)
    )

    for rel, content in files.items():
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    (project / "manifests" / "README.md").write_text("# Manifests\n")
    (project / ".gitignore").write_text(_GITIGNORE)
    (project / "README.md").write_text(f"# {name}\n\nRun `uv run rlab doctor`.\n")
    return project


def write_skeleton(root: Path, kind: str, name: str) -> Path:
    """Generate an annotated skeleton file for `rlab new <kind> <name>`."""
    template = _NEW_TEMPLATES.get(kind)
    if template is None:
        raise ValueError(f"Unknown skeleton kind {kind!r}; available: {', '.join(_NEW_TEMPLATES)}")
    content = template.format(name=name)
    # Derive a sensible output path: kind determines directory
    dir_map = {
        "experiment": "experiments",
        "benchmark": "benchmarks",
        "workflow": "workflows",
        "ingest": "ingest",
        "report": "reports",
        "adapter": "adapters",
        "causal-experiment": "experiments",
    }
    directory = root / dir_map.get(kind, kind)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name.replace('.', '_')}.py"
    path.write_text(content)
    return path


def lock_project(project: Path) -> None:
    result = subprocess.run(
        ("uv", "lock"),
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
