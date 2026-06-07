from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from rlab.manifests.dataset import DatasetManifest

T = TypeVar("T", bound=BaseModel)


def write_manifest(path: Path, manifest: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False))


def read_dataset_manifest(path: Path) -> DatasetManifest:
    return DatasetManifest.model_validate(yaml.safe_load(path.read_text()))
