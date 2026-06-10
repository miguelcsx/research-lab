from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rlab.constants import RunStatus
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.experiments.service import run_experiment
from rlab.manifests.dataset import DatasetAudit, DatasetManifest, DatasetOutput
from rlab.manifests.io import write_manifest
from rlab.manifests.run import RunManifest
from rlab.runs.layout import RunLayout
from rlab.runs.writer import RunWriter

SMOKE_EXPERIMENT = Path("experiments") / "000_smoke.py"


def runtime_for(project: Path) -> RuntimeContext:
    return build_runtime(project)


def run_smoke_experiment(project: Path, runtime: RuntimeContext | None = None) -> Path:
    active_runtime = runtime or build_runtime(project)
    result = run_experiment(active_runtime, project / SMOKE_EXPERIMENT)
    assert isinstance(result, Path)
    return result


def create_run_layout(path: Path) -> RunLayout:
    layout = RunLayout(root=path)
    layout.create()
    return layout


def create_metric_run(path: Path, metrics: dict[str, float] | None = None) -> Path:
    layout = create_run_layout(path)
    writer = RunWriter(layout)
    for name, value in (metrics or {"accuracy": 0.9}).items():
        writer.metric(name, value)
    return layout.root


def run_manifest(name: str = "run") -> RunManifest:
    now = datetime.now(UTC)
    return RunManifest(
        kind="run",
        name=name,
        version="1",
        operation="test",
        status=RunStatus.CREATED,
        created_at=now,
        updated_at=now,
    )


def write_dataset(project: Path, name: str = "sample", content: str = "value") -> Path:
    data = project / f"{name}.txt"
    data.write_text(content, encoding="utf-8")
    return data


def write_dataset_manifest_file(project: Path, name: str = "sample") -> Path:
    data = write_dataset(project, name)
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    audit_root = project / "audit"
    audit_root.mkdir(exist_ok=True)
    audit_files = {
        filename: audit_root / filename
        for filename in (
            "summary.json",
            "drop_reasons.csv",
            "stage_summary.csv",
            "source_summary.csv",
        )
    }
    for path in audit_files.values():
        path.write_text("", encoding="utf-8")
    manifest = DatasetManifest(
        kind="dataset",
        name=name,
        version="1.0.0",
        declaration=f"dataset:{name}@1.0.0",
        pipeline=f"pipeline:{name}@1.0.0",
        audit=DatasetAudit(
            kind="dataset_audit",
            name="audit",
            version="1.0.0",
            summary=audit_files["summary.json"],
            drop_reasons=audit_files["drop_reasons.csv"],
            stage_summary=audit_files["stage_summary.csv"],
            source_summary=audit_files["source_summary.csv"],
        ),
        outputs={
            "data": DatasetOutput(
                kind="dataset_output",
                name="data",
                version="1.0.0",
                path=data,
                sha256=digest,
                size_bytes=data.stat().st_size,
            )
        },
    )
    manifest_path = project / "manifests" / f"{name}.yaml"
    write_manifest(manifest_path, manifest)
    return manifest_path


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def create_git_repository(path: Path) -> tuple[Path, str]:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(("git", "init"), cwd=path, check=True, capture_output=True)
    subprocess.run(("git", "config", "user.email", "test@example.com"), cwd=path, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=path, check=True)
    (path / "file.txt").write_text("value", encoding="utf-8")
    subprocess.run(("git", "add", "file.txt"), cwd=path, check=True)
    subprocess.run(
        ("git", "-c", "commit.gpgsign=false", "commit", "-m", "initial"),
        cwd=path,
        check=True,
        capture_output=True,
    )
    revision = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=path,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    return path, revision
