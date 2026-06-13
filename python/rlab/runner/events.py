"""Runner protocol event helpers."""

from __future__ import annotations

import traceback
from collections.abc import Iterable
from datetime import datetime, timezone

from rlab._protocol import PROTOCOL_VERSION, HostRequest, base_event, emit_event
from rlab._typing import JsonObject, JsonValue

from .constants import (
    EVENT_COMPLETED,
    EVENT_FAILED,
    EVENT_METRIC,
    EVENT_REGISTRY_RECORD,
    KEY_DATA,
    KEY_DIRECTION,
    KEY_ERROR,
    KEY_EVENT_TYPE,
    KEY_KIND,
    KEY_MESSAGE,
    KEY_METRIC,
    KEY_NAME,
    KEY_PROTOCOL_VERSION,
    KEY_RECORD,
    KEY_REQUEST_ID,
    KEY_RESULT,
    KEY_SAFE_TRACEBACK,
    KEY_SCHEMA_VERSION,
    KEY_SOURCE,
    KEY_TIMESTAMP,
    KEY_UNIT,
    KEY_VALUE,
    RUNNER_SOURCE,
    SCHEMA_VERSION,
)
from .serde import jsonable


def rfc3339_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def metric_payload(
    name: str,
    value: float,
    *,
    unit: str | None = None,
    direction: str | None = None,
) -> JsonObject:
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_NAME: str(name),
        KEY_VALUE: float(value),
        KEY_UNIT: unit,
        KEY_DIRECTION: direction,
        KEY_TIMESTAMP: rfc3339_now(),
    }


def event(request: HostRequest, event_type: str, **fields: JsonValue) -> JsonObject:
    payload = base_event(request, event_type)
    payload.update(fields)
    return payload


def metric_event(request: HostRequest, name: str, value: float) -> JsonObject:
    return event(request, EVENT_METRIC, metric=metric_payload(name, value))


def emit_completed(request: HostRequest, data: object) -> None:
    emit_event(
        event(
            request,
            EVENT_COMPLETED,
            result={KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_DATA: jsonable(data)},
        )
    )


def emit_registry_records(request: HostRequest, records: Iterable[JsonObject]) -> None:
    for record in records:
        emit_event(event(request, EVENT_REGISTRY_RECORD, record=record))


def emit_failure(request_id: str, exc: Exception) -> None:
    emit_event(
        {
            KEY_PROTOCOL_VERSION: PROTOCOL_VERSION,
            KEY_REQUEST_ID: request_id,
            KEY_EVENT_TYPE: EVENT_FAILED,
            KEY_ERROR: {
                KEY_SCHEMA_VERSION: SCHEMA_VERSION,
                KEY_KIND: "python_exception",
                KEY_MESSAGE: f"{type(exc).__name__}: {exc}",
                KEY_SAFE_TRACEBACK: traceback.format_exc(),
                KEY_SOURCE: RUNNER_SOURCE,
            },
        }
    )
