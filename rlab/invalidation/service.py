from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rlab.artifacts.audit import AuditTrail
from rlab.artifacts.lineage import ArtifactLineageGraph
from rlab.invalidation.model import ImpactReport, InvalidationRecord
from rlab.runs.index import RunIndex
from rlab.runs.lifecycle import mark_stale


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class InvalidationService:
    def __init__(
        self,
        lineage: ArtifactLineageGraph,
        run_index: RunIndex,
        audit: AuditTrail,
    ) -> None:
        self.lineage = lineage
        self.run_index = run_index
        self.audit = audit
        self._records: list[InvalidationRecord] = []

    def invalidate(
        self,
        subject: str,
        reason: str,
        *,
        invalidated_by: str | None = None,
        runs_dir: Path | None = None,
    ) -> InvalidationRecord:
        affected_downstream = self.lineage.descendants(subject)
        record = InvalidationRecord(
            subject=subject,
            reason=reason,
            invalidated_at=_now(),
            invalidated_by=invalidated_by,
            affected=affected_downstream,
        )
        self._records.append(record)

        # Mark affected runs as stale
        if runs_dir and runs_dir.exists():
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir() and run_dir.name in affected_downstream:
                    mark_stale(run_dir)

        self.audit.record(
            "invalidate",
            subject,
            actor=invalidated_by,
            reason=reason,
            metadata={"affected": list(affected_downstream)},
        )
        return record

    def compute_impact(self, subject: str) -> ImpactReport:
        descendants = self.lineage.descendants(subject)
        affected_runs = tuple(d for d in descendants if d.startswith("run:"))
        affected_artifacts = tuple(d for d in descendants if ":" in d and not d.startswith("run:"))
        return ImpactReport(
            subject=subject,
            affected_runs=affected_runs,
            affected_artifacts=affected_artifacts,
            total_affected=len(descendants),
        )
