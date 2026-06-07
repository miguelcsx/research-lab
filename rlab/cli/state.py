from pathlib import Path

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext


class CliState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    console: Console
    json_output: bool = False

    def runtime(self, overrides: tuple[str, ...] = ()) -> RuntimeContext:
        return build_runtime(self.root, overrides)
