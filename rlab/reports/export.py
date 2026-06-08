from __future__ import annotations

import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from rlab.reports.markdown import render_run_report


def freeze_run(run_dir: Path, name: str, output_dir: Path) -> Path:
    """Create a frozen copy of a run with a named label."""
    dest = output_dir / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(run_dir, dest)
    (dest / "frozen.txt").write_text(
        f"Frozen from: {run_dir}\nAt: {datetime.now(tz=timezone.utc).isoformat()}\n"
    )
    return dest


def export_repro_zip(run_dir: Path, output: Path | None = None) -> Path:
    """Package a run into a portable reproduction ZIP."""
    out = output or run_dir.parent / f"{run_dir.name}_repro.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in run_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(run_dir.parent))
    return out


def export_paper_package(
    run_dirs: tuple[Path, ...],
    name: str,
    output_dir: Path,
) -> Path:
    """Build a paper-ready package from one or more run directories."""
    package = output_dir / name
    package.mkdir(parents=True, exist_ok=True)

    (package / "README.md").write_text(f"# {name}\n\nPaper reproduction package.\n")

    for run_dir in run_dirs:
        dest = package / "runs" / run_dir.name
        shutil.copytree(run_dir, dest, dirs_exist_ok=True)
        report_txt = render_run_report(run_dir)
        (package / "reports" / f"{run_dir.name}.md").parent.mkdir(parents=True, exist_ok=True)
        (package / "reports" / f"{run_dir.name}.md").write_text(report_txt)

    return package


def generate_methods_section(run_dir: Path) -> str:
    """Generate a draft methods section from run metadata."""
    from rlab.runs.reader import RunReader
    reader = RunReader(run_dir)

    if reader.layout.manifest_file.exists():
        manifest = reader.manifest()
        operation = manifest.operation
        tags = ", ".join(manifest.tags) if manifest.tags else "none"
    else:
        operation = "experiment"
        tags = "none"

    params = reader.params()
    param_text = ""
    if params:
        items = [f"{k}={v}" for k, v in sorted(params.items())]
        param_text = f"Parameters: {', '.join(items)}."

    return (
        f"We ran {operation} (run ID: {run_dir.name}, tags: {tags}). "
        f"{param_text} "
        "Results were recorded with rlab and are available in the reproduction package."
    )


def generate_citation_cff(name: str, version: str, authors: list[str]) -> str:
    """Generate a CITATION.cff entry for the project."""
    author_lines = "".join(
        f"  - name: {author}\n" for author in authors
    )
    return (
        f"cff-version: 1.2.0\n"
        f"message: If you use this software, please cite it.\n"
        f"title: {name}\n"
        f"version: {version}\n"
        f"date-released: {datetime.now(tz=timezone.utc).date().isoformat()}\n"
        f"authors:\n{author_lines}"
    )


def lock_run(run_dir: Path) -> None:
    """Mark a run as locked against further modification."""
    (run_dir / ".locked").write_text(datetime.now(tz=timezone.utc).isoformat() + "\n")


def is_locked(run_dir: Path) -> bool:
    return (run_dir / ".locked").exists()
