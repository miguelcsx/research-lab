from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.context.runtime import RuntimeContext


class DataContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    runtime: RuntimeContext
    work_dir: Path
