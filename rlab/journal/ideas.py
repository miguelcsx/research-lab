from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.constants import IdeaStatus


class Idea(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str
    status: IdeaStatus = IdeaStatus.IDEA
    linked_runs: tuple[str, ...] = ()
    created_at: str = ""
    tags: tuple[str, ...] = ()


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _idea_id() -> str:
    import uuid
    return uuid.uuid4().hex[:8]


def add_idea(path: Path, text: str, *, tags: tuple[str, ...] = ()) -> Idea:
    idea = Idea(id=_idea_id(), text=text, created_at=_now(), tags=tags)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, list_ideas(path) + (idea,))
    return idea


def list_ideas(path: Path, *, status: IdeaStatus | None = None) -> tuple[Idea, ...]:
    if not path.exists():
        return ()
    ideas = tuple(
        Idea.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    )
    if status:
        ideas = tuple(i for i in ideas if i.status == status)
    return ideas


def promote_idea(path: Path, idea_id: str, *, status: IdeaStatus) -> Idea | None:
    ideas = list(list_ideas(path))
    for i, idea in enumerate(ideas):
        if idea.id == idea_id:
            ideas[i] = idea.model_copy(update={"status": status})
            _write(path, tuple(ideas))
            return ideas[i]
    return None


def link_idea(path: Path, idea_id: str, run_id: str) -> Idea | None:
    ideas = list(list_ideas(path))
    for i, idea in enumerate(ideas):
        if idea.id == idea_id:
            new_runs = tuple(set(idea.linked_runs) | {run_id})
            ideas[i] = idea.model_copy(update={"linked_runs": new_runs})
            _write(path, tuple(ideas))
            return ideas[i]
    return None


def _write(path: Path, ideas: tuple[Idea, ...]) -> None:
    path.write_text("\n".join(i.model_dump_json() for i in ideas) + "\n")
