from pathlib import Path


def render_run_report(run_dir: Path) -> str:
    """Render a markdown report for a completed run."""
    from rlab.runs.reader import RunReader
    reader = RunReader(run_dir)

    lines: list[str] = []
    lines.append(f"# Run Report: {run_dir.name}\n")

    try:
        manifest = reader.manifest()
        lines.append(f"**Operation:** {manifest.operation}")
        lines.append(f"**Status:** {manifest.status.value}")
        lines.append(f"**Created:** {manifest.created_at.isoformat()}")
        if manifest.tags:
            lines.append(f"**Tags:** {', '.join(manifest.tags)}")
        lines.append("")
    except Exception:
        pass

    params = reader.params()
    if params:
        lines.append("## Parameters\n")
        lines.append("| Parameter | Value |")
        lines.append("|---|---|")
        for k, v in sorted(params.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    metrics = reader.metrics_summary()
    if metrics:
        lines.append("## Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for k, v in sorted(metrics.items()):
            lines.append(f"| {k} | {v:.6g} |")
        lines.append("")

    figures = reader.figures()
    if figures:
        lines.append("## Figures\n")
        for fig in figures:
            rel = fig.relative_to(run_dir)
            lines.append(f"- [{fig.name}]({rel})")
        lines.append("")

    tables = reader.tables()
    if tables:
        lines.append("## Tables\n")
        for tbl in tables:
            rel = tbl.relative_to(run_dir)
            lines.append(f"- [{tbl.name}]({rel})")
        lines.append("")

    notes = reader.notes()
    if notes:
        lines.append("## Notes\n")
        for note in notes:
            ts = note.get("timestamp", "")
            text = note.get("text", "")
            lines.append(f"- *{ts}*: {text}")
        lines.append("")

    return "\n".join(lines)
