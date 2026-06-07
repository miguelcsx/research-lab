from contextlib import suppress
from pathlib import Path

from rlab.artifacts.service import local_store, promote_path
from rlab.benchmarks.service import run_benchmark
from rlab.context.runtime import RuntimeContext
from rlab.data.service import build, diff, profile, promote, sample
from rlab.errors import RegistryError
from rlab.evaluations.service import run_evaluation
from rlab.experiments.plan import ExecutionPlan
from rlab.experiments.service import run_experiment
from rlab.reporting.compare import compare_runs
from rlab.reproducibility.service import reproduce, reproduction_plan
from rlab.runs.reader import RunReader
from rlab.testing.assertions import assert_metric_exists, assert_valid_run_dir


def test_benchmark_evaluation_experiment_and_reproduction(
    project: Path, runtime: RuntimeContext
) -> None:
    benchmark = run_benchmark(
        runtime, "tokenizer:project.byte", "project.tokenizer.length", repeat=2, warmup=1
    )
    assert_valid_run_dir(benchmark)
    assert_metric_exists(benchmark, "tokens")
    evaluation = run_evaluation(
        runtime,
        "project.quick",
        "model:project.constant",
        split="validation",
        limit=10,
        batch_size=2,
        device="cpu",
        save_predictions=True,
        upload=True,
    )
    assert_metric_exists(evaluation, "score.score")
    evaluation_manifest = RunReader(evaluation).manifest()
    assert evaluation_manifest.parameters["split"] == "validation"
    assert local_store(runtime).get("evaluation", "project.quick", "candidate").exists()
    plan = run_experiment(runtime, project / "experiments" / "000_smoke.py", dry_run=True)
    assert isinstance(plan, ExecutionPlan)
    experiment = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(experiment, Path)
    assert_valid_run_dir(experiment)
    assert reproduction_plan(experiment)
    reproduced = reproduce(runtime, experiment)
    assert isinstance(reproduced, Path)
    rows = compare_runs((benchmark, evaluation, experiment))
    assert len(rows) == 3


def test_experiment_resume_and_seed(project: Path, runtime: RuntimeContext) -> None:
    experiment = project / "experiments" / "000_smoke.py"
    first = run_experiment(runtime, experiment, seed=7)
    assert isinstance(first, Path)
    resumed = run_experiment(runtime, experiment, resume=first, run_name="continued")

    assert isinstance(resumed, Path)
    reader = RunReader(resumed)
    assert reader.manifest().parent_run == RunReader(first).manifest().name
    assert reader.results()["steps"] == []


def test_data_and_artifact_workflow(project: Path, runtime: RuntimeContext) -> None:
    first = build(runtime, "dataset:project.tiny", "1")
    second = build(runtime, "dataset:project.tiny", "2")
    first_manifest = first / "artifacts" / "dataset" / "manifest.yaml"
    second_manifest = second / "artifacts" / "dataset" / "manifest.yaml"
    assert profile(first_manifest)["records"] == 2
    assert len(sample(first_manifest, 1)) == 1
    assert diff(first_manifest, second_manifest)["removed"] == ()
    promoted = promote(runtime, first_manifest, name="project.tiny", alias="candidate")
    assert promoted.exists()
    store = local_store(runtime)
    assert store.get("dataset", "project.tiny", "candidate") == promoted
    manual = project / "manual.txt"
    manual.write_text("artifact")
    assert promote_path(
        runtime,
        manual,
        artifact_kind="text",
        name="manual",
        version="1",
        alias="approved",
    ).exists()


def test_failed_run_is_persisted(runtime: RuntimeContext) -> None:
    with suppress(RegistryError):
        run_benchmark(runtime, "model:project.constant", "project.tokenizer.length")
    failed = max(runtime.paths.runs.iterdir(), key=lambda path: path.stat().st_mtime)
    manifest = (failed / "run.yaml").read_text()
    assert "status: failed" in manifest
