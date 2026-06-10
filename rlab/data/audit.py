from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, cast

from rlab.data.model import AuditPolicy, DataAction, DataDecision
from rlab.typing import JsonValue

SUMMARY_FILE = "summary.json"
DECISIONS_FILE = "decisions.jsonl"
DROP_REASONS_FILE = "drop_reasons.csv"
STAGE_SUMMARY_FILE = "stage_summary.csv"
SOURCE_SUMMARY_FILE = "source_summary.csv"
SAMPLES_DIRECTORY = "samples"


@dataclass(frozen=True, slots=True)
class AuditPaths:
    root: Path
    summary: Path
    drop_reasons: Path
    stage_summary: Path
    source_summary: Path
    decisions: Path | None
    samples: Mapping[str, Path]


class AuditRecorder:
    def __init__(self, root: Path, policy: AuditPolicy) -> None:
        self.root = root
        self.policy = policy
        self.actions: Counter[str] = Counter()
        self.drop_reasons: Counter[str] = Counter()
        self.stage_actions: dict[str, Counter[str]] = defaultdict(Counter)
        self.source_counts: dict[str, dict[str, int]] = {}
        self._decisions: list[dict[str, JsonValue]] = []
        self._samples: dict[str, list[dict[str, JsonValue]]] = defaultdict(list)

    def record_source(self, source: str, *, read: int, emitted: int) -> None:
        self.source_counts[source] = {"read": read, "emitted": emitted}

    def record_stage(self, stage: str, *, received: int, emitted: int) -> None:
        counts = self.stage_actions[stage]
        counts["received"] = received
        counts["emitted"] = emitted

    def record_decision(
        self,
        *,
        stage: str,
        source: str,
        position: int,
        decision: DataDecision[Any],
        input_record: object,
    ) -> None:
        action = decision.action.value
        self.actions[action] += 1
        self.stage_actions[stage][action] += 1
        if decision.action is DataAction.DROP:
            self.drop_reasons[decision.reason] += 1
        row: dict[str, JsonValue] = {
            "stage": stage,
            "source": source,
            "position": position,
            "action": action,
            "reason": decision.reason,
            "metrics": dict(decision.metrics),
        }
        if self.policy.capture_decisions:
            self._decisions.append(row)
        sample_limit = self.policy.sample_reasons.get(decision.reason)
        samples = self._samples[decision.reason]
        if sample_limit is not None and len(samples) < sample_limit:
            samples.append({**row, "record": _json_value(input_record)})

    def write(self) -> AuditPaths:
        self.root.mkdir(parents=True, exist_ok=True)
        summary = self.root / SUMMARY_FILE
        drop_reasons = self.root / DROP_REASONS_FILE
        stage_summary = self.root / STAGE_SUMMARY_FILE
        source_summary = self.root / SOURCE_SUMMARY_FILE
        summary.write_text(
            json.dumps(
                {
                    "actions": dict(sorted(self.actions.items())),
                    "drop_reasons": dict(sorted(self.drop_reasons.items())),
                    "stages": len(self.stage_actions),
                    "sources": len(self.source_counts),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        _write_csv(
            drop_reasons,
            ("reason", "count"),
            ({"reason": reason, "count": count} for reason, count in self.drop_reasons.items()),
        )
        _write_csv(
            stage_summary,
            ("stage", "received", "emitted", *tuple(action.value for action in DataAction)),
            (
                {
                    "stage": stage,
                    **{key: counts.get(key, 0) for key in ("received", "emitted")},
                    **{action.value: counts.get(action.value, 0) for action in DataAction},
                }
                for stage, counts in self.stage_actions.items()
            ),
        )
        _write_csv(
            source_summary,
            ("source", "read", "emitted"),
            (
                {"source": source, **counts}
                for source, counts in self.source_counts.items()
            ),
        )

        decisions_path: Path | None = None
        if self.policy.capture_decisions:
            decisions_path = self.root / DECISIONS_FILE
            _write_jsonl(decisions_path, self._decisions)

        sample_paths: dict[str, Path] = {}
        if self.policy.sample_reasons:
            sample_root = self.root / SAMPLES_DIRECTORY
            sample_root.mkdir(parents=True, exist_ok=True)
            for reason, rows in self._samples.items():
                path = sample_root / f"{_safe_name(reason)}.jsonl"
                _write_jsonl(path, rows)
                sample_paths[reason] = path
        return AuditPaths(
            root=self.root,
            summary=summary,
            drop_reasons=drop_reasons,
            stage_summary=stage_summary,
            source_summary=source_summary,
            decisions=decisions_path,
            samples=sample_paths,
        )


def _write_csv(
    path: Path,
    columns: tuple[str, ...],
    rows: object,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(cast(Any, rows))


def _write_jsonl(path: Path, rows: list[dict[str, JsonValue]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            stream.write("\n")


def _json_value(value: object) -> JsonValue:
    if is_dataclass(value) and not isinstance(value, type):
        return cast(JsonValue, asdict(cast(Any, value)))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(JsonValue, model_dump(mode="json"))
    return cast(JsonValue, value)


def _safe_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "-_." else "_"
        for character in value
    )
