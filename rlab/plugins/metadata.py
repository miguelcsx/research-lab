from pydantic import BaseModel, ConfigDict


class PluginMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    package: str
    entrypoint: str
    capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    loaded: bool = False
    error: str | None = None
