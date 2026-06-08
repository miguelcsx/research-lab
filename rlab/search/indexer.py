from pathlib import Path

import yaml

from rlab.runs.reader import RunReader
from rlab.search.index import SearchIndex


def index_run(run_dir: Path, search: SearchIndex) -> None:
    """Index all textual content from a run directory."""
    reader = RunReader(run_dir)

    if reader.layout.manifest_file.exists():
        manifest = reader.manifest()
        title = manifest.name
        operation = manifest.operation
    else:
        title = run_dir.name
        operation = "unknown"

    body_parts: list[str] = [title, operation]

    for note in reader.notes():
        body_parts.append(str(note.get("text", "")))

    params = reader.params()
    if params:
        body_parts.append(" ".join(f"{k}={v}" for k, v in params.items()))

    search.index(
        item_id=f"run:{run_dir.name}",
        kind="run",
        title=title,
        body=" ".join(body_parts),
        path=run_dir,
    )


def index_artifact(manifest_path: Path, search: SearchIndex) -> None:
    """Index an artifact manifest."""
    if not manifest_path.is_file():
        return
    try:
        data = yaml.safe_load(manifest_path.read_text()) or {}
    except yaml.YAMLError:
        return

    name = str(data.get("name", manifest_path.stem))
    _kind = str(data.get("kind", "artifact"))
    body = " ".join(str(v) for v in data.values() if isinstance(v, str))

    search.index(
        item_id=f"artifact:{name}",
        kind="artifact",
        title=name,
        body=body,
        path=manifest_path,
    )


def rebuild_index(project_root: Path, search: SearchIndex) -> int:
    """Walk runs/ and manifests/ and re-index everything. Returns count."""
    count = 0
    runs_dir = project_root / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir() and (run_dir / "run.yaml").exists():
                index_run(run_dir, search)
                count += 1
    for manifests_dir in [project_root / "manifests", project_root / "artifacts"]:
        if manifests_dir.exists():
            for manifest in manifests_dir.rglob("*.yaml"):
                index_artifact(manifest, search)
                count += 1
    return count
