from __future__ import annotations

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
    assert RunReader(evaluation).manifest().parameters["split"] == "validation"
    assert local_store(runtime).get("evaluation", "project.quick", "candidate").exists()

    dry_run = run_experiment(runtime, project / "experiments" / "000_smoke.py", dry_run=True)
    assert isinstance(dry_run, ExecutionPlan)
    experiment = run_experiment(runtime, project / "experiments" / "000_smoke.py")
    assert isinstance(experiment, Path)
    assert reproduction_plan(experiment)
    assert isinstance(reproduce(runtime, experiment), Path)
    assert len(compare_runs((benchmark, evaluation, experiment))) == 3


def test_experiment_resume_and_data_artifact_workflow(
    project: Path, runtime: RuntimeContext
) -> None:
    first = run_experiment(runtime, project / "experiments" / "000_smoke.py", seed=7)
    assert isinstance(first, Path)
    resumed = run_experiment(
        runtime, project / "experiments" / "000_smoke.py", resume=first, run_name="continued"
    )
    assert isinstance(resumed, Path)
    assert RunReader(resumed).manifest().parent_run == RunReader(first).manifest().name

    data_v1 = build(runtime, "dataset:project.tiny", "1")
    data_v2 = build(runtime, "dataset:project.tiny", "2")
    manifest_v1 = data_v1 / "artifacts" / "dataset" / "manifest.yaml"
    manifest_v2 = data_v2 / "artifacts" / "dataset" / "manifest.yaml"
    assert profile(manifest_v1)["records"] == 2
    assert len(sample(manifest_v1, 1)) == 1
    assert diff(manifest_v1, manifest_v2)["removed"] == ()
    assert promote(runtime, manifest_v1, name="project.tiny", alias="candidate").exists()

    manual = project / "manual.txt"
    manual.write_text("artifact", encoding="utf-8")
    assert promote_path(
        runtime, manual, artifact_kind="text", name="manual", version="1", alias="approved"
    ).exists()


def test_failed_run_is_persisted(runtime: RuntimeContext) -> None:
    with suppress(RegistryError):
        run_benchmark(runtime, "model:project.constant", "project.tokenizer.length")

    failed = max(runtime.paths.runs.iterdir(), key=lambda path: path.stat().st_mtime)
    assert "status: failed" in (failed / "run.yaml").read_text(encoding="utf-8")
