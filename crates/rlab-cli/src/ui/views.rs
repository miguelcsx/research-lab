use std::fs;
use std::path::{Path, PathBuf};

use base64::{engine::general_purpose, Engine as _};
use rlab_core::{
    config::ProjectPaths,
    run::{inspect_run, list_runs},
    ArtifactStore, RlabError, RlabResult,
};
use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Clone, Serialize)]
pub struct SummaryItem {
    pub label: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct KeyValueItem {
    pub key: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct RunRow {
    pub id: String,
    pub target: String,
    pub kind: String,
    pub status: String,
    pub created: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ArtifactRow {
    pub label: String,
    pub reference: String,
    pub version: String,
    pub storage: String,
    pub size: String,
    pub created: String,
    pub digest: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ArtifactDetail {
    pub reference: String,
    pub fields: Vec<KeyValueItem>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReportSummary {
    pub run_id: String,
    pub target: String,
    pub created: String,
    pub name: String,
    pub metric_count: usize,
    pub badges: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReportBundle {
    pub run_id: String,
    pub name: String,
    pub metrics: Vec<KeyValueItem>,
    pub sections: Vec<ReportSection>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReportSection {
    pub kind: String,
    pub name: String,
    pub html: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct SectionCard {
    pub run_id: String,
    pub target: String,
    pub created: String,
    pub report_name: String,
    pub kind: String,
    pub name: String,
    pub html: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct RunsView {
    pub summaries: Vec<SummaryItem>,
    pub runs: Vec<RunRow>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RunDetailView {
    pub id: String,
    pub target: String,
    pub status: String,
    pub created: String,
    pub path: String,
    pub params: Vec<KeyValueItem>,
    pub metrics: Vec<KeyValueItem>,
    pub reports: Vec<ReportBundle>,
    pub artifacts: Vec<KeyValueItem>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ArtifactsView {
    pub summaries: Vec<SummaryItem>,
    pub artifacts: Vec<ArtifactRow>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReportsView {
    pub reports: Vec<ReportSummary>,
}

#[derive(Debug, Clone, Serialize)]
pub struct SectionsView {
    pub cards: Vec<SectionCard>,
}

#[derive(Debug, Clone, Serialize)]
pub struct CompareColumn {
    pub id: String,
    pub target: String,
    pub status: String,
    pub created: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct CompareRow {
    pub label: String,
    pub values: Vec<String>,
    pub differs: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct CompareView {
    pub selected: bool,
    pub runs: Vec<RunRow>,
    pub columns: Vec<CompareColumn>,
    pub metric_rows: Vec<CompareRow>,
    pub param_rows: Vec<CompareRow>,
}

#[derive(Debug, Clone)]
struct ReportSource {
    name: String,
    path: PathBuf,
    manifest: Value,
}

/// `list_runs` orders by run id (operation+name first), so it is alphabetical
/// rather than chronological. Re-sort on the timestamp embedded in the id so
/// every list shows the most recent runs first.
fn sorted_runs(paths: &ProjectPaths) -> RlabResult<Vec<rlab_core::run::RunSummary>> {
    let mut runs = list_runs(paths)?;
    runs.sort_by(|left, right| run_sort_token(&right.id).cmp(run_sort_token(&left.id)));
    Ok(runs)
}

fn run_sort_token(id: &str) -> &str {
    id.rsplit('_').next().unwrap_or(id)
}

pub fn runs_view(paths: &ProjectPaths) -> RlabResult<RunsView> {
    let runs = sorted_runs(paths)?;
    let completed = runs
        .iter()
        .filter(|run| run.status.as_str() == "completed")
        .count();
    let failed = runs
        .iter()
        .filter(|run| run.status.as_str() == "failed")
        .count();
    Ok(RunsView {
        summaries: vec![
            summary("Runs", runs.len()),
            summary("Completed", completed),
            summary("Failed", failed),
        ],
        runs: runs
            .into_iter()
            .map(|run| RunRow {
                target: format!("{}:{}", run.operation, run.name),
                kind: run.operation.clone(),
                status: run.status.as_str().to_string(),
                created: run_timestamp(&run.id).unwrap_or_default(),
                id: run.id,
                path: run.path,
            })
            .collect(),
    })
}

pub fn run_detail_view(paths: &ProjectPaths, id: &str) -> RlabResult<RunDetailView> {
    let details = inspect_run(paths, id)?;
    let params = read_json(&details.run.path.join("params.json"))?;
    let reports = reports_for_run(details.run.id.as_str(), &details.run.path)?
        .into_iter()
        .map(|report| report_bundle(details.run.id.as_str(), report))
        .collect::<RlabResult<Vec<_>>>()?;
    let artifacts = details
        .artifacts
        .iter()
        .map(|artifact| {
            let name = artifact
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or("artifact");
            let kind = artifact
                .get("kind")
                .and_then(Value::as_str)
                .unwrap_or("file");
            let target = artifact
                .get("artifact_ref")
                .or_else(|| artifact.get("path"))
                .or_else(|| artifact.get("object_path"))
                .and_then(Value::as_str)
                .unwrap_or("");
            KeyValueItem {
                key: format!("{kind}: {name}"),
                value: target.to_string(),
            }
        })
        .collect();
    Ok(RunDetailView {
        id: details.run.id.as_str().to_string(),
        target: format!("{}:{}", details.run.operation, details.run.name),
        status: details.run.status.as_str().to_string(),
        created: run_timestamp(details.run.id.as_str()).unwrap_or_default(),
        path: details.run.path.display().to_string(),
        params: object_items(&params),
        metrics: object_items(&details.metrics),
        reports,
        artifacts,
    })
}

pub fn artifacts_view(paths: &ProjectPaths) -> RlabResult<ArtifactsView> {
    let mut artifacts = ArtifactStore::new(paths).list(None, None, None)?;
    artifacts.sort_by(|left, right| right.created_at.cmp(&left.created_at));
    Ok(ArtifactsView {
        summaries: vec![summary("Artifacts", artifacts.len())],
        artifacts: artifacts
            .into_iter()
            .map(|artifact| {
                let reference = format!(
                    "artifact:{}/{}@{}",
                    artifact.reference.kind, artifact.reference.name, artifact.reference.version
                );
                ArtifactRow {
                    label: format!("{}/{}", artifact.reference.kind, artifact.reference.name),
                    reference,
                    version: artifact.reference.version,
                    storage: artifact.storage_type.as_str().to_string(),
                    size: format_size(artifact.size_bytes),
                    created: format_datetime(artifact.created_at),
                    digest: artifact.sha256,
                }
            })
            .collect(),
    })
}

pub fn artifact_detail_view(paths: &ProjectPaths, reference: &str) -> RlabResult<ArtifactDetail> {
    let manifest = ArtifactStore::new(paths).describe(reference)?;
    let value = serde_json::to_value(&manifest).map_err(RlabError::serialization)?;
    Ok(ArtifactDetail {
        reference: reference.to_string(),
        fields: object_items(&value),
    })
}

pub fn reports_view(paths: &ProjectPaths) -> RlabResult<ReportsView> {
    let mut reports = Vec::new();
    for run in sorted_runs(paths)? {
        let target = format!("{}:{}", run.operation, run.name);
        let created = run_timestamp(&run.id).unwrap_or_default();
        for report in reports_for_run(&run.id, Path::new(&run.path))? {
            reports.push(report_summary(&run.id, &target, &created, &report));
        }
    }
    Ok(ReportsView { reports })
}

pub fn report_detail_view(
    paths: &ProjectPaths,
    run_id: &str,
    report_name: &str,
) -> RlabResult<ReportBundle> {
    let details = inspect_run(paths, run_id)?;
    let source = read_report(
        &details
            .run
            .path
            .join("outputs")
            .join("reports")
            .join(report_name),
    )?;
    report_bundle(run_id, source)
}

pub fn sections_view(paths: &ProjectPaths, kind: &str) -> RlabResult<SectionsView> {
    let mut cards = Vec::new();
    for run in sorted_runs(paths)? {
        for report in reports_for_run(&run.id, Path::new(&run.path))? {
            if let Some(sections) = report.manifest.get("sections").and_then(Value::as_array) {
                for section in sections {
                    if section.get("type").and_then(Value::as_str) != Some(kind) {
                        continue;
                    }
                    let name = section.get("name").and_then(Value::as_str).unwrap_or(kind);
                    cards.push(SectionCard {
                        run_id: run.id.clone(),
                        target: format!("{}:{}", run.operation, run.name),
                        created: run_timestamp(&run.id).unwrap_or_default(),
                        report_name: report.name.clone(),
                        kind: kind.to_string(),
                        name: name.to_string(),
                        html: render_section_body(&report.path, section)?,
                    });
                }
            }
        }
    }
    Ok(SectionsView { cards })
}

pub fn compare_view(paths: &ProjectPaths, run_ids: &[String]) -> RlabResult<CompareView> {
    if run_ids.is_empty() {
        return Ok(CompareView {
            selected: false,
            runs: runs_view(paths)?.runs,
            columns: Vec::new(),
            metric_rows: Vec::new(),
            param_rows: Vec::new(),
        });
    }

    let mut columns = Vec::new();
    let mut metric_maps = Vec::new();
    let mut param_maps = Vec::new();
    for id in run_ids {
        let details = inspect_run(paths, id)?;
        columns.push(CompareColumn {
            target: format!("{}:{}", details.run.operation, details.run.name),
            status: details.run.status.as_str().to_string(),
            created: run_timestamp(details.run.id.as_str()).unwrap_or_default(),
            id: details.run.id.as_str().to_string(),
        });
        metric_maps.push(items_map(&details.metrics));
        let params = read_json(&details.run.path.join("params.json"))?;
        param_maps.push(items_map(&params));
    }

    Ok(CompareView {
        selected: true,
        runs: Vec::new(),
        metric_rows: compare_rows(&metric_maps),
        param_rows: compare_rows(&param_maps),
        columns,
    })
}

fn items_map(value: &Value) -> std::collections::BTreeMap<String, String> {
    object_items(value)
        .into_iter()
        .map(|item| (item.key, item.value))
        .collect()
}

fn compare_rows(maps: &[std::collections::BTreeMap<String, String>]) -> Vec<CompareRow> {
    let mut keys = std::collections::BTreeSet::new();
    for map in maps {
        keys.extend(map.keys().cloned());
    }
    keys.into_iter()
        .map(|key| {
            let values: Vec<String> = maps
                .iter()
                .map(|map| map.get(&key).cloned().unwrap_or_else(|| "—".to_string()))
                .collect();
            let differs = values.iter().collect::<std::collections::BTreeSet<_>>().len() > 1;
            CompareRow {
                label: key,
                values,
                differs,
            }
        })
        .collect()
}

fn report_summary(
    run_id: &str,
    target: &str,
    created: &str,
    report: &ReportSource,
) -> ReportSummary {
    let sections = report
        .manifest
        .get("sections")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let metric_count = report
        .manifest
        .get("metrics")
        .and_then(Value::as_object)
        .map_or(0, serde_json::Map::len);
    ReportSummary {
        run_id: run_id.to_string(),
        target: target.to_string(),
        created: created.to_string(),
        name: report.name.clone(),
        metric_count,
        badges: section_badges(&sections),
    }
}

fn report_bundle(run_id: &str, report: ReportSource) -> RlabResult<ReportBundle> {
    let metrics = object_items(report.manifest.get("metrics").unwrap_or(&Value::Null));
    let mut sections = Vec::new();
    if let Some(values) = report.manifest.get("sections").and_then(Value::as_array) {
        for section in values {
            let kind = section
                .get("type")
                .and_then(Value::as_str)
                .unwrap_or("section");
            let name = section.get("name").and_then(Value::as_str).unwrap_or(kind);
            sections.push(ReportSection {
                kind: kind.to_string(),
                name: name.to_string(),
                html: render_section_body(&report.path, section)?,
            });
        }
    }
    Ok(ReportBundle {
        run_id: run_id.to_string(),
        name: report.name,
        metrics,
        sections,
    })
}

fn reports_for_run(_run_id: &str, run_path: &Path) -> RlabResult<Vec<ReportSource>> {
    let report_root = run_path.join("outputs").join("reports");
    if !report_root.is_dir() {
        return Ok(Vec::new());
    }
    let mut reports = Vec::new();
    for entry in fs::read_dir(&report_root).map_err(|error| RlabError::io(&report_root, error))? {
        let path = entry
            .map_err(|error| RlabError::io(&report_root, error))?
            .path();
        if path.join("report_manifest.json").is_file() {
            reports.push(read_report(&path)?);
        }
    }
    reports.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(reports)
}

fn read_report(path: &Path) -> RlabResult<ReportSource> {
    let manifest = read_json(&path.join("report_manifest.json"))?;
    let name = manifest
        .get("name")
        .and_then(Value::as_str)
        .or_else(|| path.file_name().and_then(|value| value.to_str()))
        .unwrap_or("report")
        .to_string();
    Ok(ReportSource {
        name,
        path: path.to_path_buf(),
        manifest,
    })
}

fn render_section_body(root: &Path, section: &Value) -> RlabResult<String> {
    let kind = section
        .get("type")
        .and_then(Value::as_str)
        .unwrap_or("section");
    let rel = section.get("path").and_then(Value::as_str).unwrap_or("");
    let path = root.join(rel);
    match kind {
        "table" => render_table_file(&path),
        "figure" => render_figure_file(&path),
        "markdown" => render_markdown_file(&path),
        "json" => Ok(render_json_block(&read_json(&path)?)),
        _ => Ok(format!("<p><code>{}</code></p>", escape(rel))),
    }
}

fn render_table_file(path: &Path) -> RlabResult<String> {
    match path.extension().and_then(|value| value.to_str()) {
        Some("csv") => {
            render_csv_table(&fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?)
        }
        Some("json") => Ok(render_json_table(&read_json(path)?)),
        Some("jsonl") => render_jsonl_table(
            &fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?,
        ),
        _ => Ok(format!(
            "<p><code>{}</code></p>",
            escape(&path.display().to_string())
        )),
    }
}

fn render_csv_table(text: &str) -> RlabResult<String> {
    Ok(render_rows_table(&parse_csv_rows(text)))
}

fn render_jsonl_table(text: &str) -> RlabResult<String> {
    let values = text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .collect::<Vec<_>>();
    Ok(render_json_table(&Value::Array(values)))
}

fn render_json_table(value: &Value) -> String {
    match value {
        Value::Array(rows) => render_value_rows(rows),
        Value::Object(_) => render_json_value(value),
        _ => format!("<p>{}</p>", escape(&value.to_string())),
    }
}

fn render_json_block(value: &Value) -> String {
    match value {
        Value::Null => "<p class=\"muted\">No data.</p>".to_string(),
        Value::Array(_) | Value::Object(_) => {
            format!(
                "<div class=\"table-shell compact json-shell\">{}</div>",
                render_json_value(value)
            )
        }
        _ => format!("<p>{}</p>", escape(&format_value(value))),
    }
}

/// Render arbitrary JSON as nested key/value tables instead of dumping a raw
/// string blob. Arrays of like-shaped objects become a single columnar table.
fn render_json_value(value: &Value) -> String {
    match value {
        Value::Object(map) if !map.is_empty() => {
            let mut html = String::from("<table class=\"json-table\"><tbody>");
            for (key, child) in map {
                html.push_str(&format!(
                    "<tr><th>{}</th><td>{}</td></tr>",
                    escape(key),
                    render_json_value(child)
                ));
            }
            html.push_str("</tbody></table>");
            html
        }
        Value::Array(items) if !items.is_empty() => {
            if items.iter().all(Value::is_object) {
                return render_value_rows(items);
            }
            // Tuples/vectors of scalars read better inline than as a bullet list.
            if items.iter().all(|item| !item.is_object() && !item.is_array()) {
                return escape(
                    &items
                        .iter()
                        .map(format_value)
                        .collect::<Vec<_>>()
                        .join(", "),
                );
            }
            let mut html = String::from("<ul class=\"json-list\">");
            for item in items {
                html.push_str(&format!("<li>{}</li>", render_json_value(item)));
            }
            html.push_str("</ul>");
            html
        }
        Value::Array(_) | Value::Object(_) => "<span class=\"muted\">empty</span>".to_string(),
        _ => escape(&format_value(value)),
    }
}

fn render_value_rows(rows: &[Value]) -> String {
    let mut columns = std::collections::BTreeSet::new();
    for row in rows {
        if let Some(object) = row.as_object() {
            columns.extend(object.keys().cloned());
        }
    }
    let columns = columns.into_iter().collect::<Vec<_>>();
    let mut table_rows = Vec::new();
    table_rows.push(columns.clone());
    for row in rows.iter().take(100) {
        let object = row.as_object();
        table_rows.push(
            columns
                .iter()
                .map(|column| {
                    object
                        .and_then(|row| row.get(column))
                        .map(format_value)
                        .unwrap_or_default()
                })
                .collect(),
        );
    }
    render_rows_table(&table_rows)
}

fn render_rows_table(rows: &[Vec<String>]) -> String {
    if rows.is_empty() {
        return "<p class=\"muted\">No rows.</p>".to_string();
    }
    let mut html = String::from("<div class=\"table-shell compact\"><table><thead><tr>");
    for header in &rows[0] {
        html.push_str(&format!("<th>{}</th>", escape(header)));
    }
    html.push_str("</tr></thead><tbody>");
    for row in rows.iter().skip(1) {
        html.push_str("<tr>");
        for value in row {
            html.push_str(&format!("<td>{}</td>", escape(value)));
        }
        html.push_str("</tr>");
    }
    html.push_str("</tbody></table></div>");
    html
}

fn parse_csv_rows(text: &str) -> Vec<Vec<String>> {
    text.lines().map(parse_csv_line).collect()
}

fn parse_csv_line(line: &str) -> Vec<String> {
    let mut cells = Vec::new();
    let mut current = String::new();
    let mut quoted = false;
    let mut chars = line.chars().peekable();
    while let Some(ch) = chars.next() {
        match ch {
            '"' if quoted && chars.peek() == Some(&'"') => {
                current.push('"');
                chars.next();
            }
            '"' => quoted = !quoted,
            ',' if !quoted => {
                cells.push(current.clone());
                current.clear();
            }
            _ => current.push(ch),
        }
    }
    cells.push(current);
    cells
}

fn render_figure_file(path: &Path) -> RlabResult<String> {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("figure")
        .to_string();
    let src = embed_image(path)?;
    Ok(format!(
        "<figure><img class=\"figure-preview\" src=\"{}\" alt=\"{}\" loading=\"lazy\"><figcaption>{}</figcaption></figure>",
        src,
        escape(&name),
        escape(&name),
    ))
}

/// Read an image file and return a `data:` URL so figures render inline without
/// the UI needing to serve run files over HTTP.
fn embed_image(path: &Path) -> RlabResult<String> {
    let bytes = fs::read(path).map_err(|error| RlabError::io(path, error))?;
    let mime = match path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_ascii_lowercase()
        .as_str()
    {
        "jpg" | "jpeg" => "image/jpeg",
        "webp" => "image/webp",
        "svg" => "image/svg+xml",
        "gif" => "image/gif",
        _ => "image/png",
    };
    let data = general_purpose::STANDARD.encode(bytes);
    Ok(format!("data:{mime};base64,{data}"))
}

fn render_markdown_file(path: &Path) -> RlabResult<String> {
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    let root = path.parent().unwrap_or_else(|| Path::new("."));
    Ok(render_markdown(&text, root))
}

fn render_markdown(text: &str, root: &Path) -> String {
    let mut html = String::from("<div class=\"markdown\">");
    let lines = text.lines().collect::<Vec<_>>();
    let mut index = 0;
    while index < lines.len() {
        let line = lines[index];
        let trimmed = line.trim();

        // Pipe tables.
        if index + 1 < lines.len()
            && is_markdown_table_line(line)
            && is_markdown_table_separator(lines[index + 1])
        {
            let mut rows = vec![markdown_table_cells(line)];
            index += 2;
            while index < lines.len() && is_markdown_table_line(lines[index]) {
                rows.push(markdown_table_cells(lines[index]));
                index += 1;
            }
            html.push_str(&render_rows_table(&rows));
            continue;
        }

        // Bullet lists (`-`, `*`, `+`).
        if is_markdown_bullet(trimmed) {
            html.push_str("<ul>");
            while index < lines.len() && is_markdown_bullet(lines[index].trim()) {
                let item = &lines[index].trim()[2..];
                html.push_str(&format!("<li>{}</li>", render_inline(item)));
                index += 1;
            }
            html.push_str("</ul>");
            continue;
        }

        // Ordered lists (`1.`, `2.` …).
        if is_markdown_ordered(trimmed) {
            html.push_str("<ol>");
            while index < lines.len() && is_markdown_ordered(lines[index].trim()) {
                let item = lines[index]
                    .trim()
                    .splitn(2, ". ")
                    .nth(1)
                    .unwrap_or_default();
                html.push_str(&format!("<li>{}</li>", render_inline(item)));
                index += 1;
            }
            html.push_str("</ol>");
            continue;
        }

        if let Some(image) = markdown_image(trimmed, root) {
            html.push_str(&image);
        } else if let Some(title) = trimmed.strip_prefix("#### ") {
            html.push_str(&format!("<h4>{}</h4>", render_inline(title)));
        } else if let Some(title) = trimmed.strip_prefix("### ") {
            html.push_str(&format!("<h4>{}</h4>", render_inline(title)));
        } else if let Some(title) = trimmed.strip_prefix("## ") {
            html.push_str(&format!("<h3>{}</h3>", render_inline(title)));
        } else if let Some(title) = trimmed.strip_prefix("# ") {
            html.push_str(&format!("<h2>{}</h2>", render_inline(title)));
        } else if let Some(quote) = trimmed.strip_prefix("> ") {
            html.push_str(&format!("<blockquote>{}</blockquote>", render_inline(quote)));
        } else if trimmed == "---" || trimmed == "***" || trimmed == "___" {
            html.push_str("<hr>");
        } else if trimmed.is_empty() {
            // Paragraph break; collapse runs of blank lines.
        } else {
            html.push_str(&format!("<p>{}</p>", render_inline(line)));
        }
        index += 1;
    }
    html.push_str("</div>");
    html
}

fn is_markdown_bullet(trimmed: &str) -> bool {
    matches!(trimmed.get(0..2), Some("- ") | Some("* ") | Some("+ "))
}

fn is_markdown_ordered(trimmed: &str) -> bool {
    let digits: String = trimmed.chars().take_while(char::is_ascii_digit).collect();
    !digits.is_empty() && trimmed[digits.len()..].starts_with(". ")
}

/// Render a standalone `![alt](path)` line as an embedded figure. Relative paths
/// are resolved against the report directory; unreadable images fall back to a
/// caption so the section still renders.
fn markdown_image(line: &str, root: &Path) -> Option<String> {
    let rest = line.strip_prefix("![")?;
    let (alt, rest) = rest.split_once("](")?;
    let path = rest.strip_suffix(')')?;
    if path.starts_with("http://") || path.starts_with("https://") {
        return Some(format!(
            "<figure><img class=\"figure-preview\" src=\"{}\" alt=\"{}\" loading=\"lazy\"><figcaption>{}</figcaption></figure>",
            escape(path),
            escape(alt),
            escape(alt),
        ));
    }
    match resolve_markdown_image(root, path).and_then(|resolved| embed_image(&resolved).ok()) {
        Some(src) => Some(format!(
            "<figure><img class=\"figure-preview\" src=\"{}\" alt=\"{}\" loading=\"lazy\"><figcaption>{}</figcaption></figure>",
            src,
            escape(alt),
            escape(alt),
        )),
        None => Some(format!(
            "<p class=\"muted\">Missing figure: <code>{}</code></p>",
            escape(path)
        )),
    }
}

/// Resolve a markdown image reference to a file on disk. Reports often copy the
/// markdown into a bundle directory without co-locating its figures, so when the
/// direct relative path misses we fall back to searching the run tree by name.
fn resolve_markdown_image(root: &Path, rel: &str) -> Option<PathBuf> {
    let direct = root.join(rel);
    if direct.is_file() {
        return Some(direct);
    }
    let run_root = run_root_of(root)?;
    let name = Path::new(rel).file_name()?;
    find_file_named(&run_root.join("outputs"), name, 8)
        .or_else(|| find_file_named(&run_root, name, 4))
}

/// Walk up from `start` until we find the run directory (the one holding
/// `run.json`).
fn run_root_of(start: &Path) -> Option<PathBuf> {
    let mut current = Some(start);
    while let Some(dir) = current {
        if dir.join("run.json").is_file() {
            return Some(dir.to_path_buf());
        }
        current = dir.parent();
    }
    None
}

/// Bounded depth-first search for the first file with the given name.
fn find_file_named(dir: &Path, name: &std::ffi::OsStr, depth: usize) -> Option<PathBuf> {
    if depth == 0 || !dir.is_dir() {
        return None;
    }
    let entries = fs::read_dir(dir).ok()?;
    let mut subdirs = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file() {
            if path.file_name() == Some(name) {
                return Some(path);
            }
        } else if path.is_dir() {
            subdirs.push(path);
        }
    }
    subdirs
        .into_iter()
        .find_map(|sub| find_file_named(&sub, name, depth - 1))
}

/// Apply inline markdown (code spans, bold, italics, links) over escaped text.
fn render_inline(text: &str) -> String {
    let mut out = String::new();
    // Code spans are protected from further formatting.
    for (index, segment) in text.split('`').enumerate() {
        if index % 2 == 1 {
            out.push_str(&format!("<code>{}</code>", escape(segment)));
        } else {
            out.push_str(&apply_links(&apply_emphasis(&escape(segment))));
        }
    }
    out
}

fn apply_emphasis(escaped: &str) -> String {
    let bolded = wrap_delimited(escaped, "**", "strong");
    let bolded = wrap_delimited(&bolded, "__", "strong");
    wrap_delimited(&bolded, "*", "em")
}

fn wrap_delimited(input: &str, delim: &str, tag: &str) -> String {
    let parts: Vec<&str> = input.split(delim).collect();
    if parts.len() < 3 {
        return input.to_string();
    }
    let mut out = String::new();
    for (index, part) in parts.iter().enumerate() {
        // Only wrap fully matched (odd-indexed) segments; trailing unmatched
        // delimiters are re-emitted verbatim.
        if index % 2 == 1 && index != parts.len() - 1 {
            out.push_str(&format!("<{tag}>{part}</{tag}>"));
        } else {
            if index % 2 == 1 {
                out.push_str(delim);
            }
            out.push_str(part);
        }
    }
    out
}

fn apply_links(escaped: &str) -> String {
    let mut out = String::new();
    let mut rest = escaped;
    while let Some(open) = rest.find('[') {
        out.push_str(&rest[..open]);
        let tail = &rest[open..];
        let Some(mid) = tail.find("](") else {
            out.push_str(tail);
            return out;
        };
        let Some(end) = tail[mid + 2..].find(')') else {
            out.push_str(tail);
            return out;
        };
        let label = &tail[1..mid];
        let url = &tail[mid + 2..mid + 2 + end];
        if url.starts_with("http://") || url.starts_with("https://") || url.starts_with('/') {
            out.push_str(&format!("<a href=\"{url}\">{label}</a>"));
        } else {
            out.push_str(&format!("[{label}]({url})"));
        }
        rest = &tail[mid + 2 + end + 1..];
    }
    out.push_str(rest);
    out
}

fn is_markdown_table_line(line: &str) -> bool {
    let trimmed = line.trim();
    trimmed.starts_with('|') && trimmed.ends_with('|') && trimmed.matches('|').count() >= 2
}

fn is_markdown_table_separator(line: &str) -> bool {
    if !is_markdown_table_line(line) {
        return false;
    }
    markdown_table_cells(line).iter().all(|cell| {
        let trimmed = cell.trim();
        !trimmed.is_empty() && trimmed.chars().all(|ch| matches!(ch, '-' | ':' | ' '))
    })
}

fn markdown_table_cells(line: &str) -> Vec<String> {
    line.trim()
        .trim_matches('|')
        .split('|')
        .map(|cell| cell.trim().to_string())
        .collect()
}

fn object_items(value: &Value) -> Vec<KeyValueItem> {
    let Some(object) = value.as_object().filter(|object| !object.is_empty()) else {
        return Vec::new();
    };
    object
        .iter()
        .map(|(key, value)| KeyValueItem {
            key: key.clone(),
            value: format_value(value),
        })
        .collect()
}

fn section_badges(sections: &[Value]) -> Vec<String> {
    let mut counts: std::collections::BTreeMap<&str, usize> = std::collections::BTreeMap::new();
    for section in sections {
        let kind = section
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or("section");
        *counts.entry(kind).or_default() += 1;
    }
    counts
        .into_iter()
        .map(|(kind, count)| format!("{count} {kind}"))
        .collect()
}

/// Pull the trailing `_YYYYMMDDTHHMMSS…Z` token out of a run id and format it as
/// `YYYY-MM-DD HH:MM`. Run ids embed their creation instant, so this avoids an
/// extra file read per row while still giving the table a sortable, readable time.
fn run_timestamp(id: &str) -> Option<String> {
    let token = id.rsplit('_').next()?;
    let (date, time) = token.split_once('T')?;
    if date.len() != 8 || !date.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let time: String = time.chars().take_while(char::is_ascii_digit).collect();
    if time.len() < 4 {
        return None;
    }
    Some(format!(
        "{}-{}-{} {}:{}",
        &date[0..4],
        &date[4..6],
        &date[6..8],
        &time[0..2],
        &time[2..4],
    ))
}

/// Format an `OffsetDateTime` as `YYYY-MM-DD HH:MM` for table display.
fn format_datetime(dt: time::OffsetDateTime) -> String {
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}",
        dt.year(),
        u8::from(dt.month()),
        dt.day(),
        dt.hour(),
        dt.minute(),
    )
}

/// Human-readable byte size (e.g. `4.2 MB`).
fn format_size(bytes: u64) -> String {
    const UNITS: [&str; 5] = ["B", "KB", "MB", "GB", "TB"];
    let mut value = bytes as f64;
    let mut unit = 0;
    while value >= 1024.0 && unit < UNITS.len() - 1 {
        value /= 1024.0;
        unit += 1;
    }
    if unit == 0 {
        format!("{bytes} B")
    } else {
        format!("{value:.1} {}", UNITS[unit])
    }
}

fn summary(label: &str, value: usize) -> SummaryItem {
    SummaryItem {
        label: label.to_string(),
        value: value.to_string(),
    }
}

fn read_json(path: &Path) -> RlabResult<Value> {
    if !path.is_file() {
        return Ok(Value::Null);
    }
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    serde_json::from_str(&text).map_err(RlabError::serialization)
}

fn format_value(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(value) => value.clone(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => value.to_string(),
        _ => serde_json::to_string(value).unwrap_or_default(),
    }
}

fn escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn markdown_pipe_tables_render_as_tables() {
        let html = render_markdown(
            "# A\n\n| one | two |\n| --- | --- |\n| 1 | 2 |\n",
            Path::new("."),
        );
        assert!(html.contains("<table>"));
        assert!(!html.contains("<p>| one | two |</p>"));
    }

    #[test]
    fn markdown_inline_formats_bold_and_links() {
        let html = render_markdown("This is **bold** and a [link](https://x.io).", Path::new("."));
        assert!(html.contains("<strong>bold</strong>"));
        assert!(html.contains("<a href=\"https://x.io\">link</a>"));
    }

    #[test]
    fn markdown_bullets_render_as_list() {
        let html = render_markdown("- one\n- two\n", Path::new("."));
        assert!(html.contains("<ul><li>one</li><li>two</li></ul>"));
    }

    #[test]
    fn json_arrays_render_as_tables() {
        let value = serde_json::json!([{"a": 1, "b": "x"}]);
        let html = render_json_table(&value);
        assert!(html.contains("<th>a</th>"));
        assert!(html.contains("<td>1</td>"));
    }
}
