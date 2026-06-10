from __future__ import annotations

from pathlib import Path

import pytest

from rlab.context.factory import build_runtime
from rlab.errors import ManifestError
from rlab.evaluations.runner import execute_external
from rlab.evaluations.service import run_evaluation
from rlab.manifests.io import read_dataset_manifest
from rlab.manifests.resolver import resolve_dataset_manifest
from rlab.manifests.validation import validate_dataset_manifest
from rlab.project.loader import load_modules
from rlab.registry.context import using_registry
from tests.helpers.factories import write_dataset_manifest_file


def test_dataset_manifest_resolution_and_validation(project: Path) -> None:
    manifest_path = write_dataset_manifest_file(project, "sample")
    runtime = build_runtime(project)

    resolved_path, resolved = resolve_dataset_manifest(runtime, "manifest:sample")
    assert resolved_path == manifest_path
    assert read_dataset_manifest(manifest_path) == resolved
    validate_dataset_manifest(resolved)

    (project / "sample.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(ManifestError):
        validate_dataset_manifest(resolved)
    with pytest.raises(ManifestError):
        resolve_dataset_manifest(runtime, "manifest:missing")


def test_external_evaluation_suite(project: Path) -> None:
    (project / "external_eval.py").write_text(
        "import json, pathlib\n"
        "pathlib.Path('external.json').write_text(json.dumps({'accuracy': 0.75}))\n",
        encoding="utf-8",
    )
    suite = project / "suites" / "external.py"
    suite.write_text(
        "from pathlib import Path\n"
        "import rlab\n"
        "lab = rlab.Project('project')\n"
        "root = Path(__file__).parents[1]\n"
        "lab.external_evaluation(\n"
        "    'project.external', version='1.0.0',\n"
        "    command=rlab.ExternalCommand(\n"
        "        args=('python', str(root / 'external_eval.py')), cwd=root),\n"
        "    parser='json', output=root / 'external.json')\n",
        encoding="utf-8",
    )

    runtime = build_runtime(project)
    with using_registry(runtime.registry):
        load_modules(project, ("suites.external",))
        # Pull the new records into runtime.registry (the loader's project
        # merge copies only the names that the test cares about).
        import sys
        module = sys.modules.get("suites.external")
        if module is not None and hasattr(module, "lab"):
            for record in module.lab.registry.list():
                runtime.registry.add(record)

    run = run_evaluation(runtime, "project.external", "hf:test/model")
    assert (run / "external" / "project.external" / "external_eval.yaml").exists()
    assert (run / "external" / "project.external" / "raw" / "external.json").exists()

    run_evaluation(runtime, "project.external", "hf:test/model", external_runner="subprocess")
    with pytest.raises(ValueError, match="docker_image"):
        run_evaluation(runtime, "project.external", "hf:test/model", external_runner="docker")
    with pytest.raises(ValueError, match="Unsupported external runner"):
        execute_external(runtime, "project.external", "hf:test/model", "cluster")
