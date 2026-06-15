"""Project registry record helpers."""

from __future__ import annotations

from collections.abc import Mapping
from rlab._typing import JsonObject, JsonValue

from .constants import (
    ERROR_INVALID_NAME,
    ERROR_KIND_NAME_REQUIRED,
    ERROR_WORKFLOW_STEPS_INVALID,
    KEY_METADATA,
    KEY_NAME,
    KEY_STEP,
    KEY_STEPS,
    VALID_NAME_EXTRA_CHARS,
)
from .serde import object_sequence


def validate_identifier(kind: str, name: str) -> None:
    if not kind.strip() or not name.strip():
        raise ValueError(ERROR_KIND_NAME_REQUIRED)

    invalid = [
        char for char in name if not (char.isalnum() or char in VALID_NAME_EXTRA_CHARS)
    ]
    if invalid:
        raise ValueError(ERROR_INVALID_NAME.format(name=name))


def workflow_step_metadata(
    step_name: str,
    record: JsonObject,
    metadata: JsonObject,
) -> JsonObject:
    values = dict(metadata)
    values.pop(KEY_STEP, None)
    return {
        KEY_NAME: step_name,
        "module": record["module"],
        "qualname": record["qualname"],
        "source": record["source"],
        KEY_METADATA: values,
    }


def workflow_steps(record: JsonObject, workflow_name: str) -> list[JsonValue]:
    metadata = record.get(KEY_METADATA)
    if not isinstance(metadata, dict):
        metadata = {}
        record[KEY_METADATA] = metadata

    steps = metadata.get(KEY_STEPS)
    if steps is None:
        steps = []
        metadata[KEY_STEPS] = steps

    if not isinstance(steps, list):
        raise ValueError(
            ERROR_WORKFLOW_STEPS_INVALID.format(workflow_name=workflow_name)
        )

    return steps


def step_name(step: JsonValue) -> str | None:
    if not isinstance(step, dict):
        return None

    name = step.get(KEY_NAME)
    return name if isinstance(name, str) else None


def dataset_sinks(metadata: Mapping[str, object]) -> list[object]:
    sinks = metadata.get("sinks")
    if sinks is not None:
        return object_sequence(sinks, "dataset sinks")

    sink = metadata.get("sink")
    if sink is None or isinstance(sink, str):
        return []

    return [sink]
