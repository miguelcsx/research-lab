from pydantic import BaseModel, ConfigDict


class ResultSchema(BaseModel):
    """Base class for custom per-experiment result schemas.

    Decorate subclasses with @rlab.result_schema("name") to register them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
