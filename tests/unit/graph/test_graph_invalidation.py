from __future__ import annotations

from pathlib import Path

from rlab.artifacts.audit import AuditTrail
from rlab.artifacts.lineage import ArtifactLineageGraph
from rlab.graph.store import KnowledgeGraph
from rlab.invalidation.model import ImpactReport
from rlab.invalidation.service import InvalidationService
from rlab.runs.index import RunIndex


def test_knowledge_graph_nodes_edges_query_and_lineage(tmp_path: Path) -> None:
    graph = KnowledgeGraph(tmp_path / "graph.db")
    graph.add_node("run:001", "run", "Run 1", {"status": "completed"})
    graph.add_node("artifact:a", "artifact", "A")
    graph.add_node("artifact:b", "artifact", "B")
    graph.add_edge("run:001", "artifact:a", "produced")
    graph.add_edge("run:001", "artifact:b", "consumed")

    assert "artifact:a" in graph.neighbors("run:001", relation="produced")
    assert "artifact:b" in graph.neighbors("run:001", relation="consumed")
    assert graph.query("SELECT * FROM graph_nodes WHERE kind = 'run'")[0]["label"] == "Run 1"
    assert ("run:001", "artifact:a") in graph.lineage("run:001")
    assert graph.neighbors("nonexistent") == ()


def test_invalidation_service_records_audit_and_impact(tmp_path: Path) -> None:
    lineage = ArtifactLineageGraph(tmp_path / "lineage.db")
    lineage.add_edge("dataset:raw", "dataset:clean")
    lineage.add_edge("dataset:clean", "run:training")
    audit = AuditTrail(tmp_path / "audit.jsonl")
    service = InvalidationService(lineage, RunIndex(tmp_path / "runs.db"), audit)

    impact = service.compute_impact("dataset:raw")
    assert impact.total_affected >= 2
    record = service.invalidate("dataset:raw", "contamination discovered")
    assert record.subject == "dataset:raw"
    assert audit.replay()[0].action == "invalidate"


def test_invalidation_without_lineage(tmp_path: Path) -> None:
    service = InvalidationService(
        ArtifactLineageGraph(tmp_path / "lineage.db"),
        RunIndex(tmp_path / "runs.db"),
        AuditTrail(tmp_path / "audit.jsonl"),
    )
    assert service.invalidate("dataset:isolated", "test").affected == ()


def test_impact_report_model() -> None:
    report = ImpactReport(
        subject="dataset:v1",
        affected_runs=("run:001",),
        affected_artifacts=("model:a", "report:x"),
        total_affected=3,
    )
    assert report.total_affected == 3
    assert "run:001" in report.affected_runs
