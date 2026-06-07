import shutil
from pathlib import Path

from rlab.context.runtime import RuntimeContext
from rlab.errors import ManifestError
from rlab.manifests.dataset import DatasetManifest
from rlab.manifests.io import read_dataset_manifest
from rlab.manifests.validation import validate_dataset_manifest


def resolve_dataset_manifest(
    runtime: RuntimeContext, reference: str
) -> tuple[Path, DatasetManifest]:
    name = reference.removeprefix("manifest:")
    candidates = (
        path
        for directory in runtime.paths.manifests
        for path in (directory / f"{name}.yaml", directory / f"{name}.yml")
    )
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        raise ManifestError(f"Dataset manifest {name!r} was not found")
    manifest = read_dataset_manifest(path)
    validate_dataset_manifest(manifest, path.parent)
    return path, manifest


def capture_dataset_manifest(runtime: RuntimeContext, reference: str) -> DatasetManifest:
    path, manifest = resolve_dataset_manifest(runtime, reference)
    if runtime.run_dir is None:
        raise RuntimeError("Manifest capture requires an active run")
    destination = runtime.run_dir / "manifests" / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return manifest
