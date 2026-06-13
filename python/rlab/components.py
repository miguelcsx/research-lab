"""Typed component specifications, requirements, and construction helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Generic

from ._typing import JsonObject, JsonValue, ParamsT, coerce_json_value


@dataclass(frozen=True, slots=True)
class ComponentSpec(Generic[ParamsT]):
    ref: str
    params: ParamsT

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
    def from_value(
        cls,
        value: str | Mapping[str, JsonValue] | "ComponentSpec[JsonObject]",
    ) -> "ComponentSpec[JsonObject]":
        if isinstance(value, ComponentSpec):
            return value
        if isinstance(value, str):
            return cls.empty(value)
        name = value.get("ref", value.get("name"))
        params = value.get("params", {})
        if not isinstance(name, str) or not name:
            raise ValueError("component spec requires a non-empty name")
        if not isinstance(params, Mapping):
            raise TypeError("component spec params must be a mapping")
        return ComponentSpec(
            ref=name, params=dict(cast(Mapping[str, JsonValue], params))
        )

    def to_dict(self) -> JsonObject:
        params = coerce_json_value(self.params)
        if not isinstance(params, dict):
            raise TypeError("component params must serialize to an object")
        return {"ref": self.ref, "params": params}


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

    def to_dict(self) -> JsonObject:
        return {
            "model_outputs": list(self.model_outputs),
            "model_heads": list(self.model_heads),
            "batch_fields": list(self.batch_fields),
            "capabilities": list(self.capabilities),
            "artifacts": list(self.artifacts),
        }


def collect_requirements(values: list[Requirements]) -> Requirements:
    result = Requirements()
    for value in values:
        result = result.merge(value)
    return result


def _union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*left, *right)))


__all__ = ["ComponentSpec", "Requirements", "collect_requirements"]
