import subprocess
from pathlib import Path

LAB_TOML = """\
[project]
name = "{name}"

[plugins]
autoload = true
modules = ["components", "benchmarks", "suites", "data"]

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
"""

PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["{rlab_dependency}"]

[dependency-groups]
dev = ["pytest", "ruff", "mypy"]
"""

SMOKE = """\
import rlab


@rlab.experiment("000_smoke")
def experiment() -> rlab.Experiment:
    return rlab.Experiment(
        question="Does the generated project execute?",
        matrix={
            "target": ["tokenizer:project.byte"],
            "model": ["model:project.constant"],
        },
        benchmarks=("project.tokenizer.length",),
        evaluations=("project.quick",),
    )
"""

COMPONENT = """\
import rlab


@rlab.component("tokenizer", "project.byte")
class ByteTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(text.encode())

    def decode(self, ids: list[int]) -> str:
        return bytes(ids).decode()
"""

MODEL = """\
import rlab


@rlab.component("model", "project.constant")
class ConstantModel:
    def __call__(self, inputs: object) -> float:
        return 1.0
"""

BENCHMARK = """\
import rlab


@rlab.benchmark("project.tokenizer.length", target="tokenizer")
def length(target: object, ctx: rlab.BenchmarkContext) -> dict[str, float]:
    tokens = target.encode("research")
    return {"tokens": float(len(tokens))}
"""

SUITE = """\
import rlab


def score(model: object, ctx: rlab.RuntimeContext) -> dict[str, float]:
    return {"score": float(model(None))}


@rlab.suite("project.quick")
def quick() -> rlab.EvaluationSuite:
    return rlab.EvaluationSuite(
        tasks=(rlab.EvaluationTask(name="score", evaluator=score),),
    )
"""

DATA = """\
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


def write_project(root: Path, name: str) -> Path:
    project = root / name
    project.mkdir(parents=True, exist_ok=False)
    for directory in (
        "experiments",
        "components",
        "benchmarks",
        "suites",
        "data",
        "manifests",
        "runs",
        "artifacts",
        "reports",
        "tests",
    ):
        (project / directory).mkdir()
    for package in ("components", "benchmarks", "suites", "data"):
        (project / package / "__init__.py").write_text("")
    (project / "lab.toml").write_text(LAB_TOML.format(name=name))
    source = Path(__file__).parents[2]
    dependency = (
        f"rlab @ {source.as_uri()}" if (source / "pyproject.toml").exists() else "rlab>=0.1"
    )
    (project / "pyproject.toml").write_text(PYPROJECT.format(name=name, rlab_dependency=dependency))
    (project / "experiments" / "000_smoke.py").write_text(SMOKE)
    (project / "components" / "tokenizers.py").write_text(COMPONENT)
    (project / "components" / "models.py").write_text(MODEL)
    (project / "benchmarks" / "custom.py").write_text(BENCHMARK)
    (project / "suites" / "project_eval.py").write_text(SUITE)
    (project / "data" / "tiny.py").write_text(DATA)
    (project / "manifests" / "README.md").write_text("# Dataset manifests\n")
    (project / ".gitignore").write_text(".venv/\n.rlab/\nruns/\nartifacts/\n")
    (project / "README.md").write_text(f"# {name}\n\nRun `uv run rlab doctor`.\n")
    return project


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
