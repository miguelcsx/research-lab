from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rationale: str
    selected_run: str | None = None
    criteria: dict[str, str] = Field(default_factory=dict)
    created_at: str = ""
    author: str | None = None


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def add_decision(
    path: Path,
    rationale: str,
    *,
    selected_run: str | None = None,
    criteria: dict[str, str] | None = None,
    author: str | None = None,
) -> Decision:
    decision = Decision(
        rationale=rationale,
        selected_run=selected_run,
        criteria=criteria or {},
        created_at=_now(),
        author=author,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(decision.model_dump_json() + "\n")
    return decision


def list_decisions(path: Path) -> tuple[Decision, ...]:
    if not path.exists():
        return ()
    return tuple(
        Decision.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    )
