from pathlib import Path

from rlab.manifests.base import Manifest


class ModelManifest(Manifest):
    model_ref: str
    checkpoint: Path
    architecture: str
    tokenizer: str | None = None
    training_run: str | None = None
    parameter_count: int | None = None
    license: str | None = None
