from __future__ import annotations

from pathlib import Path

import rlab
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.service import _metric_key, run_evaluation
from rlab.registry.context import using_registry
from rlab.runs.reader import RunReader
from rlab.testing.assertions import assert_metric_exists


def test_metric_key_prefixes_unqualified_names() -> None:
    assert _metric_key("suite.fast", "score", "accuracy") == "score.accuracy"


def test_metric_key_keeps_qualified_names() -> None:
    assert _metric_key("suite.fast", "score", "score.accuracy") == "score.accuracy"
    assert _metric_key("suite.fast", "score", "suite.fast.accuracy") == "suite.fast.accuracy"


def test_run_evaluation_without_model_and_with_params(
    project: Path, runtime: RuntimeContext
) -> None:
    with using_registry(runtime.registry):

        @rlab.evaluation("test.prepare", "download")
        def download(model: object, ctx: RuntimeContext) -> dict[str, float]:
            assert model == ""
            assert ctx.params["track"] == "strict"
            return {"completed": 1.0}

    run_root = run_evaluation(runtime, "test.prepare", params={"track": "strict"})

    assert_metric_exists(run_root, "download.completed")
    parameters = RunReader(run_root).manifest().parameters
    assert parameters["track"] == "strict"
    assert parameters["model"] == ""
