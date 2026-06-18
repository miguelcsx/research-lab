"""Typed component specifications, requirements, and construction helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Generic, cast

from ._typing import JsonObject, ParamsT, coerce_json_value


@dataclass(frozen=True, slots=True)
class ComponentSpec(Generic[ParamsT]):
    ref: str
    params: ParamsT = field(default_factory=dict)

    @classmethod
    def __class_getitem__(cls, _item: object) -> type["ComponentSpec[object]"]:
        return cls

    @classmethod
    def empty(cls, ref: str) -> "ComponentSpec[JsonObject]":
        return ComponentSpec(ref=ref, params={})

    @property
    def name(self) -> str:
        return self.ref.rsplit(":", 1)[-1]

    @property
    def kind(self) -> str | None:
        return self.ref.split(":", 1)[0] if ":" in self.ref else None

    @classmethod
    def from_value(cls, value: object) -> "ComponentSpec[JsonObject]":
        if isinstance(value, ComponentSpec):
            return value
        if isinstance(value, str):
            return cls.empty(value)
        if not isinstance(value, Mapping):
            raise TypeError(f"component spec must be a string or mapping, got {type(value).__name__}")
        name = value.get("ref", value.get("reference", value.get("name")))
        params = (
            value["params"]
            if "params" in value
            else {
                key: child
                for key, child in value.items()
                if key not in {"ref", "reference", "name"}
            }
        )
        if not isinstance(name, str) or not name:
            raise ValueError("component spec requires a non-empty name")
        if not isinstance(params, Mapping):
            raise TypeError("component spec params must be a mapping")
        return ComponentSpec(
            ref=name, params={str(k): coerce_json_value(v) for k, v in params.items()}
        )

    def to_dict(self) -> JsonObject:
        params = coerce_json_value(self.params)
        if not isinstance(params, dict):
            raise TypeError("component params must serialize to an object")
        return {"ref": self.ref, "params": params}

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ) -> Any:
        core_schema = cast(Any, import_module("pydantic_core")).core_schema

        return core_schema.no_info_plain_validator_function(
            cls.from_value,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: value.to_dict()
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: object,
        _handler: object,
    ) -> JsonObject:
        return {
            "anyOf": [
                {"type": "string"},
                {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string"},
                        "name": {"type": "string"},
                        "params": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            ]
        }


@dataclass(frozen=True, slots=True)
class Requirements:
    """Capabilities and data required by a registered component."""

    model_outputs: tuple[str, ...] = ()
    model_heads: tuple[str, ...] = ()
    batch_fields: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()

    def merge(self, other: "Requirements") -> "Requirements":
        return Requirements(
            model_outputs=_union(self.model_outputs, other.model_outputs),
            model_heads=_union(self.model_heads, other.model_heads),
            batch_fields=_union(self.batch_fields, other.batch_fields),
            capabilities=_union(self.capabilities, other.capabilities),
            artifacts=_union(self.artifacts, other.artifacts),
        )

    def only(self, *fields: str) -> "Requirements":
        selected = set(fields)
        return Requirements(
            **{
                field: getattr(self, field) if field in selected else ()
                for field in _REQUIREMENT_FIELDS
            }
        )

    def without(self, *fields: str) -> "Requirements":
        removed = set(fields)
        return Requirements(
            **{
                field: () if field in removed else getattr(self, field)
                for field in _REQUIREMENT_FIELDS
            }
        )

    def to_dict(self) -> JsonObject:
        return {
            "model_outputs": list(self.model_outputs),
            "model_heads": list(self.model_heads),
            "batch_fields": list(self.batch_fields),
            "capabilities": list(self.capabilities),
            "artifacts": list(self.artifacts),
        }


@dataclass(frozen=True, slots=True)
class ComponentContract:
    """Requirements consumed and produced by a registered component."""

    requires: Requirements = Requirements()
    provides: Requirements = Requirements()

    def merge(self, other: "ComponentContract") -> "ComponentContract":
        return ComponentContract(
            requires=self.requires.merge(other.requires),
            provides=self.provides.merge(other.provides),
        )

    def to_dict(self) -> JsonObject:
        return {
            "requires": self.requires.to_dict(),
            "provides": self.provides.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class MissingRequirements:
    """Requirement fields requested by consumers but not offered by providers."""

    model_outputs: tuple[str, ...] = ()
    model_heads: tuple[str, ...] = ()
    batch_fields: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not any(self.to_dict().values())

    def to_dict(self) -> JsonObject:
        return {
            "model_outputs": list(self.model_outputs),
            "model_heads": list(self.model_heads),
            "batch_fields": list(self.batch_fields),
            "capabilities": list(self.capabilities),
            "artifacts": list(self.artifacts),
        }

    def raise_if_any(self, label: str = "component contract") -> None:
        if self.ok:
            return
        missing = {
            key: value
            for key, value in self.to_dict().items()
            if isinstance(value, list) and value
        }
        raise MissingRequirementsError(f"{label} is missing requirements: {missing}")


class MissingRequirementsError(ValueError):
    """Raised when required capabilities or artifacts are not provided."""


def collect_requirements(values: Iterable[Requirements]) -> Requirements:
    result = Requirements()
    for value in values:
        result = result.merge(value)
    return result


def collect_component_requirements(
    lookup: Callable[[str, str], Requirements],
    kind: str,
    specs: Iterable[ComponentSpec[object] | Mapping[str, object] | str],
) -> Requirements:
    return collect_requirements(
        [lookup(kind, ComponentSpec.from_value(spec).name) for spec in specs]
    )


def collect_contracts(values: Iterable[ComponentContract]) -> ComponentContract:
    result = ComponentContract()
    for value in values:
        result = result.merge(value)
    return result


def missing_requirements(
    required: Requirements,
    provided: Requirements,
    *,
    fields: Iterable[str] | None = None,
) -> MissingRequirements:
    selected = set(fields) if fields is not None else set(_REQUIREMENT_FIELDS)
    return MissingRequirements(
        model_outputs=_missing(required.model_outputs, provided.model_outputs)
        if "model_outputs" in selected
        else (),
        model_heads=_missing(required.model_heads, provided.model_heads)
        if "model_heads" in selected
        else (),
        batch_fields=_missing(required.batch_fields, provided.batch_fields)
        if "batch_fields" in selected
        else (),
        capabilities=_missing(required.capabilities, provided.capabilities)
        if "capabilities" in selected
        else (),
        artifacts=_missing(required.artifacts, provided.artifacts)
        if "artifacts" in selected
        else (),
    )


def _union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*left, *right)))


def _missing(required: tuple[str, ...], provided: tuple[str, ...]) -> tuple[str, ...]:
    available = set(provided)
    return tuple(value for value in required if value not in available)


_REQUIREMENT_FIELDS = (
    "model_outputs",
    "model_heads",
    "batch_fields",
    "capabilities",
    "artifacts",
)


def ref(name: str, **params: object) -> ComponentSpec[object]:
    """Create a component reference without needing a Project instance."""
    return ComponentSpec(name, params)


__all__ = [
    "ComponentContract",
    "ComponentSpec",
    "MissingRequirements",
    "MissingRequirementsError",
    "Requirements",
    "collect_component_requirements",
    "collect_contracts",
    "collect_requirements",
    "missing_requirements",
    "ref",
]
