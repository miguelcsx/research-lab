"""Native component specifications, requirements, and contracts."""

from __future__ import annotations

from rlab._rlab import (
    ComponentContract,
    ComponentSpec,
    MissingRequirements,
    MissingRequirementsError,
    Requirements,
    collect_component_requirements,
    collect_contracts,
    collect_requirements,
    missing_requirements,
)


def _component_spec_core_schema(
    cls: object, source: object, handler: object
) -> object:
    del cls, source, handler
    from pydantic_core import core_schema

    return core_schema.no_info_plain_validator_function(
        ComponentSpec.from_value,
        serialization=core_schema.plain_serializer_function_ser_schema(
            lambda value: value.to_dict(),
            return_schema=_component_spec_json_core_schema(),
        ),
        json_schema_input_schema=_component_spec_json_core_schema(),
    )


def _component_spec_json_schema(
    cls: object, schema: object, handler: object
) -> object:
    del cls, schema, handler
    return {
        "anyOf": [
            {"type": "string"},
            {
                "type": "object",
                "required": ["ref"],
                "properties": {
                    "ref": {"type": "string"},
                    "params": {"type": "object", "additionalProperties": True},
                },
                "additionalProperties": True,
            },
        ],
    }


def _component_spec_json_core_schema() -> object:
    from pydantic_core import core_schema

    return core_schema.union_schema(
        [
            core_schema.str_schema(),
            core_schema.typed_dict_schema(
                {
                    "ref": core_schema.typed_dict_field(core_schema.str_schema()),
                    "params": core_schema.typed_dict_field(
                        core_schema.dict_schema(
                            core_schema.str_schema(),
                            core_schema.any_schema(),
                        ),
                        required=False,
                    ),
                },
                extra_behavior="allow",
            ),
        ]
    )


ComponentSpec.__get_pydantic_core_schema__ = classmethod(_component_spec_core_schema)
ComponentSpec.__get_pydantic_json_schema__ = classmethod(_component_spec_json_schema)
ComponentSpec.__reduce__ = lambda self: (ComponentSpec, (self.ref, self.params))


__all__ = [
    "ComponentContract",
    "MissingRequirements",
    "MissingRequirementsError",
    "Requirements",
    "collect_component_requirements",
    "collect_contracts",
    "collect_requirements",
    "missing_requirements",
]
