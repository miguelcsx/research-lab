from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from rlab.references.refs import Reference
from rlab.typing import JsonValue


class ComponentSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: Reference
    params: Mapping[str, JsonValue] = Field(default_factory=dict)


class BuildSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    component: ComponentSpec
    cache: bool = True
