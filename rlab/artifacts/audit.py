from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    subject: str
    timestamp: str
    actor: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditTrail:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action: str,
        subject: str,
        *,
        actor: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            subject=subject,
            timestamp=datetime.now(tz=UTC).isoformat(),
            actor=actor,
            reason=reason,
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(mode="json")) + "\n")
        return event

    def replay(self) -> tuple[AuditEvent, ...]:
        if not self.path.exists():
            return ()
        events: list[AuditEvent] = []
        for raw_line in self.path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            events.append(AuditEvent.model_validate(json.loads(line)))
        return tuple(events)
