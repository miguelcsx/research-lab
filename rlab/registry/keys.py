from pydantic import BaseModel, ConfigDict, field_validator

from rlab.constants import EntryKind


class RegistryKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EntryKind
    name: str

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(char.isspace() for char in normalized):
            raise ValueError("registry names must be non-empty and contain no whitespace")
        return normalized

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.name}"


class ComponentKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    name: str

    def __str__(self) -> str:
        return f"{self.kind}:{self.name}"
