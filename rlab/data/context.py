from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rlab.context.runtime import RuntimeContext
from rlab.typing import JsonValue


class DataContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    runtime: RuntimeContext
    work_dir: Path
    params: dict[str, JsonValue] = Field(default_factory=dict)
