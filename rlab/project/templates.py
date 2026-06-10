import subprocess
from pathlib import Path
from typing import TypedDict

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
dev = ["pytest", "ruff", "mypy", "types-pyyaml"]
"""

_GITIGNORE = ".venv/\n.rlab/\nruns/\nartifacts/\n"


_SMOKE_EXPERIMENT = """\
import rlab

lab = rlab.Project("{name}")


@lab.experiment(
    "000_smoke",
    question="Does the generated project execute?",
    matrix={{"target": ["tokenizer:project.byte"]}},
    benchmarks=("project.tokenizer.length",),
)
def experiment() -> None:
    pass
"""


_COMPONENT_STUB = """\
import rlab

lab = rlab.Project("{name}")


@lab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()
"""


_MODEL_STUB = """\
import rlab

lab = rlab.Project("{name}")


@lab.component("model", "project.constant")
class ConstantModel:
    def __call__(self, inputs: object) -> float:
        return 1.0
"""


_BENCHMARK_STUB = """\
from typing import Protocol

import rlab

lab = rlab.Project("{name}")


class Encoder(Protocol):
    \"\"\"Shape this benchmark expects from its target — defined by the project.\"\"\"

    def encode(self, text: str) -> list[int]: ...


@lab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target: Encoder) -> rlab.ResultBundle:
    tokens = target.encode("research")
    return rlab.ResultBundle(
        metrics=(rlab.Metric(name="tokens", value=float(len(tokens))),),
    )
"""


_SUITE_STUB = """\
from collections.abc import Callable

import rlab

lab = rlab.Project("{name}")


@lab.evaluation("project.quick", "score")
def score(model: Callable[[object], float]) -> dict[str, float]:
    return {"score": float(model(None))}
"""


_DATA_STUB = """\
from collections.abc import Iterable
from dataclasses import dataclass

import rlab

lab = rlab.Project("{name}")


@lab.source("project.tiny")
@dataclass(frozen=True, slots=True)
class TinySource:
    limit: int = 2

    def read(self) -> Iterable[dict[str, object]]:
        records = ({"text": "research"}, {"text": "lab"})
        yield from records[: self.limit]


@lab.transform("project.uppercase")
@dataclass(frozen=True, slots=True)
class Uppercase:
    def apply(self, record: dict[str, object]) -> rlab.Decision[dict[str, object]]:
        return rlab.update({**record, "text": str(record["text"]).upper()})


tiny_pipeline = lab.pipeline(
    "project.tiny", rlab.ComponentUse("transform:project.uppercase")
)

lab.dataset(
    "project.tiny",
    source=rlab.ComponentUse("source:project.tiny"),
    pipeline=tiny_pipeline,
    sinks=(rlab.ComponentUse("sink:rlab.jsonl"),),
)
"""


_WORKFLOW_STUB = """\
import rlab

lab = rlab.Project("{name}")


@lab.workflow(
    "project.main",
    step="step_one",
    description="Main project workflow",
)
def step_one(ctx: rlab.WorkflowContext) -> None:
    ctx.note("Implement this workflow step.")
"""


_SOLVER_STUB = """\
import rlab

lab = rlab.Project("{name}")


@lab.component("solver", "project.basic")
class BasicSolver:
    def solve(self, inputs: object) -> dict[str, float]:
        return {"result": 1.0}
"""


_PROJECT_PY = """\
import rlab

lab = rlab.Project("{name}")
"""


class ProjectTemplate(TypedDict):
    modules: list[str]
    dirs: list[str]
    packages: list[str]
    files: dict[str, str]


_TEMPLATES: dict[str, ProjectTemplate] = {
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

from {project_module}.project import lab


@lab.experiment(
    "{name}",
    question="What is the research question?",
    hypothesis="What do you expect to find?",
    matrix={{
        "param": ["value_a", "value_b"],
    }},
)
def experiment() -> None:
    pass
"""

_NEW_BENCHMARK = """\
import rlab

from {project_module}.project import lab


@lab.benchmark("{name}", target="component_kind")
def benchmark(target: object) -> rlab.ResultBundle:
    return rlab.ResultBundle(
        metrics=(rlab.Metric(name="score", value=0.0),),
    )
"""

_NEW_WORKFLOW = """\
import rlab

from {project_module}.project import lab


@lab.workflow(
    "{name}",
    step="step_one",
    description="Describe what this workflow does.",
)
def step_one(ctx: rlab.WorkflowContext) -> None:
    ctx.note("Implement this workflow step.")
"""

_NEW_DATA_PIPELINE = """\
from collections.abc import Iterable
from dataclasses import dataclass

import rlab

from {project_module}.project import lab


@lab.source("{name}")
@dataclass(frozen=True, slots=True)
class Source:
    def read(self) -> Iterable[dict[str, object]]:
        yield {{"text": "example"}}


data_pipeline = lab.pipeline("{name}")

lab.dataset(
    "{name}",
    source=rlab.ComponentUse("source:{name}"),
    pipeline=data_pipeline,
    sinks=(rlab.ComponentUse("sink:rlab.jsonl"),),
)
"""

_NEW_REPORT = """\
# {name} report
# Auto-generated by rlab new report {name}

import rlab

from {project_module}.project import lab


def generate(run_dir, ctx):
    \"\"\"Custom report generator for {name}.\"\"\"
    pass
"""

_NEW_ADAPTER = """\
import rlab

from {project_module}.project import lab


@lab.adapter("{name}")
class MyAdapter(rlab.BaseAdapter):
    def command(self, ctx: rlab.AdapterContext) -> rlab.ExternalCommand:
        return rlab.ExternalCommand(
            args=("python", "-m", "evaluation_module", "--target", "{{model}}"),
        )
"""

_NEW_CAUSAL_EXPERIMENT = """\
import rlab

from {project_module}.project import lab


@lab.experiment(
    "{name}",
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
def experiment() -> None:
    pass
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
    dirs = spec["dirs"]
    packages = spec["packages"]
    module_lines = spec["modules"]
    files = spec["files"]

    for directory in dirs:
        (project / directory).mkdir(parents=True, exist_ok=True)
    for package in packages:
        pkg = project / package
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("")

    (project / "project.py").write_text(_PROJECT_PY.format(name=name))

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
        # Templates use ``{{`` and ``}}`` to denote literal Python braces
        # (dict literals, f-string syntax in user code, etc.) and ``{name}``
        # / ``{project_module}`` for substitutions. First substitute the
        # named tokens, then unescape the doubled braces.
        path.write_text(
            content.replace("{project_module}", name)
            .replace("{name}", name)
            .replace("{{", "{")
            .replace("}}", "}")
        )

    (project / "manifests" / "README.md").write_text("# Manifests\n")
    (project / ".gitignore").write_text(_GITIGNORE)
    (project / "README.md").write_text(f"# {name}\n\nRun `uv run rlab doctor`.\n")
    return project


def write_skeleton(root: Path, kind: str, name: str, project_module: str) -> Path:
    """Generate an annotated skeleton file for `rlab new <kind> <name>`.

    The skeleton imports :data:`lab` from the project's ``project.py`` so it
    shares the same Project/Registry as the rest of the project.
    """
    template = _NEW_TEMPLATES.get(kind)
    if template is None:
        raise ValueError(f"Unknown skeleton kind {kind!r}; available: {', '.join(_NEW_TEMPLATES)}")
    content = template.format(name=name, project_module=project_module)
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
