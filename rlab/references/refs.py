from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReferenceKind(StrEnum):
    COMPONENT = "component"
    BENCHMARK = "benchmark"
    SUITE = "suite"
    DATASET = "dataset"
    MANIFEST = "manifest"
    MODEL = "model"
    HF = "hf"
    HF_DATASET = "hf_dataset"
    LOCAL = "local"
    TORCH = "torch"
    MLFLOW = "mlflow"
    RUN = "run"
    ARTIFACT = "artifact"
    S3 = "s3"
    GCS = "gcs"
    SOURCE = "source"


class Reference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ReferenceKind
    value: str
    alias: str | None = None
    artifact_kind: str | None = None
    component_kind: str | None = None

    def __str__(self) -> str:
        value = self.value
        if self.artifact_kind:
            value = f"{self.artifact_kind}/{value}"
        if self.alias:
            value = f"{value}@{self.alias}"
        scheme = self.component_kind or self.kind.value
        return f"{scheme}:{value}"
