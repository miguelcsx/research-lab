from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from rlab.context.runtime import RuntimeContext
from rlab.typing import Metrics


class EvaluationTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    evaluator: Callable[[Any, RuntimeContext], Metrics]
