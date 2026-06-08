from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rlab.context.runtime import RuntimeContext


class AdapterContext(BaseModel):
    """Read-only view passed to every lifecycle method of an ExternalAdapter.

    Adapters never touch global state — they receive everything they need here.
    `inputs` carries adapter-specific parameters resolved by the caller.
    `work_dir` is a per-run sandbox where the adapter may write scratch files.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    runtime: RuntimeContext
    adapter: str
    work_dir: Path
    inputs: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)

    def with_artifacts(self, mapping: dict[str, Path]) -> AdapterContext:
        return self.model_copy(update={"artifacts": {**self.artifacts, **mapping}})
