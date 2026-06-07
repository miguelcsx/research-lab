import hashlib
from pathlib import Path

import pytest

from rlab.context.factory import build_runtime
from rlab.errors import ManifestError
from rlab.evaluations.runner import execute_external
from rlab.evaluations.service import run_evaluation
from rlab.manifests.dataset import DatasetManifest, DatasetOutput
from rlab.manifests.io import read_dataset_manifest, write_manifest
from rlab.manifests.resolver import resolve_dataset_manifest
from rlab.manifests.validation import validate_dataset_manifest


def test_manifest_resolution(project: Path) -> None:
    data = project / "data.txt"
    data.write_text("value")
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = DatasetManifest(
        kind="dataset",
        name="sample",
        version="1",
        outputs={
            "data": DatasetOutput(
                kind="dataset_output",
                name="data",
                version="1",
                path=data,
                sha256=digest,
                size_bytes=data.stat().st_size,
            )
        },
    )
    path = project / "manifests" / "sample.yaml"
    write_manifest(path, manifest)
    assert read_dataset_manifest(path) == manifest
    resolved_path, resolved = resolve_dataset_manifest(build_runtime(project), "manifest:sample")
    assert resolved_path == path
    validate_dataset_manifest(resolved)
    data.write_text("changed")
    with pytest.raises(ManifestError):
        validate_dataset_manifest(resolved)
    with pytest.raises(ManifestError):
        resolve_dataset_manifest(build_runtime(project), "manifest:missing")


def test_external_evaluation(project: Path) -> None:
    script = project / "external_eval.py"
    script.write_text(
        "import json, pathlib\n"
        "pathlib.Path('external.json').write_text(json.dumps({'accuracy': 0.75}))\n"
    )
    suite = project / "suites" / "external.py"
    suite.write_text(
        "from pathlib import Path\n"
        "import rlab\n"
        "root = Path(__file__).parents[1]\n"
        "@rlab.external_suite('project.external')\n"
        "def external():\n"
        "    return rlab.ExternalEvaluation(\n"
        "        name='project.external', version='1.0.0',\n"
        "        command=rlab.ExternalCommand(\n"
        "            args=('python', str(root / 'external_eval.py')), cwd=root),\n"
        "        parser='json', output=root / 'external.json')\n"
    )
    runtime = build_runtime(project)
    run = run_evaluation(runtime, "project.external", "hf:test/model")
    assert (run / "external" / "project.external" / "external_eval.yaml").exists()
    assert (run / "external" / "project.external" / "raw" / "external.json").exists()
    run_evaluation(
        runtime,
        "project.external",
        "hf:test/model",
        external_runner="subprocess",
    )
    with pytest.raises(ValueError, match="docker_image"):
        run_evaluation(
            runtime,
            "project.external",
            "hf:test/model",
            external_runner="docker",
        )
    with pytest.raises(ValueError, match="Unsupported external runner"):
        execute_external(runtime, "project.external", "hf:test/model", "cluster")
