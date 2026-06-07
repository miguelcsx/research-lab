from pydantic import BaseModel, ConfigDict

from rlab.project.loader import ModuleLoadResult


class ModulesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    load: tuple[str, ...] = ()


def failed_modules(results: tuple[ModuleLoadResult, ...]) -> tuple[ModuleLoadResult, ...]:
    return tuple(r for r in results if not r.loaded)


def loaded_modules(results: tuple[ModuleLoadResult, ...]) -> tuple[ModuleLoadResult, ...]:
    return tuple(r for r in results if r.loaded)
