from pathlib import Path

from rlab.errors import ManifestError
from rlab.manifests.checksum import verify_sha256
from rlab.manifests.dataset import DatasetManifest


def validate_dataset_manifest(manifest: DatasetManifest, base: Path | None = None) -> None:
    root = base or Path.cwd()
    for name, output in manifest.outputs.items():
        path = output.path if output.path.is_absolute() else root / output.path
        if not path.exists():
            raise ManifestError(f"Dataset output {name!r} does not exist: {path}")
        if not verify_sha256(path, output.sha256):
            raise ManifestError(f"Dataset output {name!r} checksum does not match")
