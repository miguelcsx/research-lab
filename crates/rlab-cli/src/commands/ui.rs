use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::Path;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::Duration;

use clap::Args;
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    run::{inspect_run, list_runs},
    ArtifactStore, RlabError, RlabResult,
};
use serde_json::Value;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct UiCommand {
    #[arg(long, default_value_t = 8787)]
    pub port: u16,
    #[arg(long)]
    pub no_open: bool,
}

pub fn run(command: UiCommand, root: Option<&Path>, as_json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let address = format!("127.0.0.1:{}", command.port);
    let listener = TcpListener::bind(&address).map_err(|error| RlabError::Run {
        message: format!("failed to bind rlab ui on {address}: {error}"),
    })?;
    let url = format!(
        "http://{}",
        listener.local_addr().map_err(|error| RlabError::Run {
            message: format!("failed to read rlab ui address: {error}"),
        })?
    );
    if as_json {
        print_json("ui", serde_json::json!({"url": url}))?;
    } else {
        print_line(&format!("rlab ui: {url}"));
    }
    if !command.no_open {
        open_url(&url);
    }
    let shutting_down = Arc::new(AtomicBool::new(false));
    install_ctrlc_handler(Arc::clone(&shutting_down))?;
    listener
        .set_nonblocking(true)
        .map_err(|error| RlabError::Run {
            message: format!("failed to make rlab ui listener nonblocking: {error}"),
        })?;
    while !shutting_down.load(Ordering::SeqCst) {
        match listener.accept() {
            Ok((stream, _)) => {
                if let Err(error) = serve(stream, &paths) {
                    if !as_json {
                        print_line(&format!("rlab ui warning: {error}"));
                    }
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(50));
            }
            Err(error) => {
                return Err(RlabError::Run {
                    message: format!("rlab ui connection failed: {error}"),
                });
            }
        }
    }
    if !as_json {
        print_line("rlab ui: stopped");
    }
    Ok(0)
}

fn install_ctrlc_handler(shutting_down: Arc<AtomicBool>) -> RlabResult<()> {
    ctrlc::set_handler(move || {
        shutting_down.store(true, Ordering::SeqCst);
    })
    .map_err(|error| RlabError::Run {
        message: format!("failed to install Ctrl-C handler: {error}"),
    })
}

fn serve(mut stream: TcpStream, paths: &ProjectPaths) -> RlabResult<()> {
    stream
        .set_nonblocking(false)
        .map_err(|error| RlabError::Run {
            message: format!("failed to configure ui connection: {error}"),
        })?;
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .map_err(|error| RlabError::Run {
            message: format!("failed to configure ui read timeout: {error}"),
        })?;
    let mut buffer = [0_u8; 4096];
    let read = stream.read(&mut buffer).map_err(|error| RlabError::Run {
        message: format!("failed to read ui request: {error}"),
    })?;
    if read == 0 {
        return Ok(());
    }
    let request = String::from_utf8_lossy(&buffer[..read]);
    let path = request
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .unwrap_or("/");
    let (status, body) = if path == "/" || path == "/runs" {
        (200, runs_page(paths)?)
    } else if let Some(id) = path.strip_prefix("/run/") {
        (200, run_detail_page(paths, id)?)
    } else if path == "/artifacts" {
        (200, artifacts_page(paths)?)
    } else if let Some(query) = path.strip_prefix("/artifact?ref=") {
        (200, artifact_detail_page(paths, &decode_query(query))?)
    } else if path == "/reports" {
        (200, reports_page(paths)?)
    } else if path == "/tables" {
        (200, typed_sections_page(paths, "Tables", "table")?)
    } else if path == "/figures" {
        (200, typed_sections_page(paths, "Figures", "figure")?)
    } else if path == "/compare" {
        (
            200,
            page(
                "Compare",
                "<p>Use run metrics and table artifacts to compare outputs.</p>",
            ),
        )
    } else if path == "/favicon.ico" {
        (204, String::new())
    } else {
        (404, page("Not Found", "<p>Unknown rlab UI route.</p>"))
    };
    let response = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\nContent-Length: {}\r\n\r\n{}",
        status,
        status_text(status),
        body.len(),
        body
    );
    stream
        .write_all(response.as_bytes())
        .map_err(|error| RlabError::Run {
            message: format!("failed to write ui response: {error}"),
        })?;
    Ok(())
}

fn status_text(status: u16) -> &'static str {
    match status {
        200 => "OK",
        204 => "No Content",
        404 => "Not Found",
        _ => "OK",
    }
}

fn runs_page(paths: &ProjectPaths) -> RlabResult<String> {
    let mut rows = String::new();
    let runs = list_runs(paths)?;
    for run in &runs {
        rows.push_str(&format!(
            "<tr><td><a href=\"/run/{}\">{}</a></td><td>{}:{}</td><td><span class=\"badge status-{}\">{}</span></td><td><code>{}</code></td></tr>",
            escape(&run.id),
            escape(&run.id),
            escape(&run.operation),
            escape(&run.name),
            escape(run.status.as_str()),
            escape(run.status.as_str()),
            escape(&run.path)
        ));
    }
    Ok(page(
        "Runs",
        &format!(
            "{}<div class=\"table-shell\"><table><thead><tr><th>Run</th><th>Target</th><th>Status</th><th>Path</th></tr></thead><tbody>{rows}</tbody></table></div>",
            summary_grid(&[
                ("Runs", runs.len().to_string()),
                (
                    "Completed",
                    runs.iter()
                        .filter(|run| run.status.as_str() == "completed")
                        .count()
                        .to_string(),
                ),
                (
                    "Failed",
                    runs.iter()
                        .filter(|run| run.status.as_str() == "failed")
                        .count()
                        .to_string(),
                ),
            ])
        ),
    ))
}

fn run_detail_page(paths: &ProjectPaths, id: &str) -> RlabResult<String> {
    let details = inspect_run(paths, id)?;
    let mut body = format!(
        "<div class=\"detail-head\"><div><p class=\"eyebrow\">{}:{}</p><h2>{}</h2></div><span class=\"badge status-{}\">{}</span></div><p><code>{}</code></p>",
        escape(&details.run.operation),
        escape(&details.run.name),
        escape(details.run.id.as_str()),
        escape(details.run.status.as_str()),
        escape(details.run.status.as_str()),
        escape(&details.run.path.display().to_string())
    );
    body.push_str(&json_block(
        "Params",
        &read_json(&details.run.path.join("params.json"))?,
    ));
    body.push_str(&json_block("Metrics", &details.metrics));
    if !details.artifacts.is_empty() {
        body.push_str("<h2>Artifacts</h2><div class=\"artifact-list\">");
        for artifact in &details.artifacts {
            let name = artifact
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or("artifact");
            let kind = artifact
                .get("kind")
                .and_then(Value::as_str)
                .unwrap_or("file");
            let path = artifact
                .get("artifact_ref")
                .or_else(|| artifact.get("path"))
                .or_else(|| artifact.get("object_path"))
                .and_then(Value::as_str)
                .unwrap_or("");
            body.push_str(&format!(
                "<section class=\"artifact-row\"><span class=\"badge\">{}</span><strong>{}</strong><code>{}</code></section>",
                escape(kind),
                escape(name),
                escape(path)
            ));
        }
        body.push_str("</div>");
    }
    Ok(page("Run Detail", &body))
}

fn artifacts_page(paths: &ProjectPaths) -> RlabResult<String> {
    let mut rows = String::new();
    let artifacts = ArtifactStore::new(paths).list(None, None, None)?;
    for artifact in &artifacts {
        rows.push_str(&format!(
            "<tr><td><a href=\"/artifact?ref=artifact:{}/{}@{}\">{}/{}</a></td><td>{}</td><td>{}</td><td><code>{}</code></td></tr>",
            escape(&artifact.reference.kind),
            escape(&artifact.reference.name),
            escape(&artifact.reference.version),
            escape(&artifact.reference.kind),
            escape(&artifact.reference.name),
            escape(&artifact.reference.version),
            escape(artifact.storage_type.as_str()),
            escape(&artifact.sha256)
        ));
    }
    Ok(page(
        "Artifacts",
        &format!(
            "{}<div class=\"table-shell\"><table><thead><tr><th>Name</th><th>Version</th><th>Storage</th><th>Digest</th></tr></thead><tbody>{rows}</tbody></table></div>",
            summary_grid(&[("Artifacts", artifacts.len().to_string())])
        ),
    ))
}

fn artifact_detail_page(paths: &ProjectPaths, reference: &str) -> RlabResult<String> {
    let manifest = ArtifactStore::new(paths).describe(reference)?;
    let body = format!(
        "<p><code>{}</code></p><pre class=\"json-block\">{}</pre>",
        escape(reference),
        escape(&serde_json::to_string_pretty(&manifest).map_err(RlabError::serialization)?)
    );
    Ok(page("Artifact Detail", &body))
}

fn reports_page(paths: &ProjectPaths) -> RlabResult<String> {
    let mut cards = String::new();
    for run in list_runs(paths)? {
        let report_root = Path::new(&run.path).join("outputs").join("reports");
        if !report_root.is_dir() {
            continue;
        }
        for entry in
            fs::read_dir(&report_root).map_err(|error| RlabError::io(&report_root, error))?
        {
            let path = entry
                .map_err(|error| RlabError::io(&report_root, error))?
                .path();
            let manifest = path.join("report_manifest.json");
            if manifest.is_file() {
                cards.push_str(&format!(
                    "<section class=\"report-card\"><div><h2>{}</h2><p><code>{}</code></p></div><pre class=\"json-block\">{}</pre></section>",
                    escape(
                        path.file_name()
                            .and_then(|value| value.to_str())
                            .unwrap_or("report")
                    ),
                    escape(&run.id),
                    escape(&fs::read_to_string(&manifest).unwrap_or_default())
                ));
            }
        }
    }
    Ok(page(
        "Reports",
        &format!("<div class=\"report-grid\">{cards}</div>"),
    ))
}

fn typed_sections_page(
    paths: &ProjectPaths,
    title: &str,
    section_type: &str,
) -> RlabResult<String> {
    let mut rows = String::new();
    for (run_id, report_name, section) in report_sections(paths, section_type)? {
        let name = section
            .get("name")
            .and_then(Value::as_str)
            .unwrap_or(section_type);
        let path = section.get("path").and_then(Value::as_str).unwrap_or("");
        rows.push_str(&format!(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td><code>{}</code></td></tr>",
            escape(&run_id),
            escape(&report_name),
            escape(name),
            escape(path)
        ));
    }
    Ok(page(
        title,
        &format!(
            "<div class=\"table-shell\"><table><thead><tr><th>Run</th><th>Report</th><th>Name</th><th>Path</th></tr></thead><tbody>{rows}</tbody></table></div>"
        ),
    ))
}

fn report_sections(
    paths: &ProjectPaths,
    section_type: &str,
) -> RlabResult<Vec<(String, String, Value)>> {
    let mut sections = Vec::new();
    for run in list_runs(paths)? {
        let report_root = Path::new(&run.path).join("outputs").join("reports");
        if !report_root.is_dir() {
            continue;
        }
        for entry in
            fs::read_dir(&report_root).map_err(|error| RlabError::io(&report_root, error))?
        {
            let path = entry
                .map_err(|error| RlabError::io(&report_root, error))?
                .path();
            let manifest = read_json(&path.join("report_manifest.json"))?;
            let report_name = manifest
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or("report")
                .to_string();
            if let Some(values) = manifest.get("sections").and_then(Value::as_array) {
                sections.extend(
                    values
                        .iter()
                        .filter(|section| {
                            section.get("type").and_then(Value::as_str) == Some(section_type)
                        })
                        .cloned()
                        .map(|section| (run.id.clone(), report_name.clone(), section)),
                );
            }
        }
    }
    Ok(sections)
}

fn page(title: &str, body: &str) -> String {
    format!(
        "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>rlab {}</title><style>{}</style></head><body><aside><div class=\"brand\">rlab</div><nav><a href=\"/runs\">Runs</a><a href=\"/artifacts\">Artifacts</a><a href=\"/reports\">Reports</a><a href=\"/tables\">Tables</a><a href=\"/figures\">Figures</a><a href=\"/compare\">Compare</a></nav></aside><main><header><p class=\"eyebrow\">Runtime explorer</p><h1>{}</h1></header>{}</main></body></html>",
        escape(title),
        ui_css(),
        escape(title),
        body
    )
}

fn summary_grid(items: &[(&str, String)]) -> String {
    let mut html = String::from("<div class=\"summary-grid\">");
    for (label, value) in items {
        html.push_str(&format!(
            "<section class=\"summary-card\"><span>{}</span><strong>{}</strong></section>",
            escape(label),
            escape(value)
        ));
    }
    html.push_str("</div>");
    html
}

fn ui_css() -> &'static str {
    "*,*:before,*:after{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;color:#18201d;background:#f3f4ef;display:grid;grid-template-columns:220px minmax(0,1fr);min-height:100vh}aside{background:#111712;color:white;padding:20px;position:sticky;top:0;height:100vh}nav{display:grid;gap:6px;margin-top:22px}nav a{color:#dfe8df;text-decoration:none;padding:9px 10px;border-radius:6px}nav a:hover{background:#243025;color:white}.brand{font-weight:800;font-size:20px;letter-spacing:0}main{padding:28px;min-width:0}header{margin-bottom:20px}h1{font-size:28px;line-height:1.1;margin:3px 0 0}h2{font-size:18px;margin:0 0 10px}.eyebrow{margin:0;color:#657064;font-size:12px;text-transform:uppercase;font-weight:700;letter-spacing:.04em}.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}.summary-card,.report-card,.artifact-row{background:white;border:1px solid #dfe3dc;border-radius:8px;padding:14px}.summary-card span{display:block;color:#657064;font-size:12px}.summary-card strong{font-size:24px}.table-shell{overflow:auto;border:1px solid #dfe3dc;border-radius:8px;background:white}table{border-collapse:collapse;width:100%;min-width:720px}th,td{border-bottom:1px solid #e6e9e4;padding:10px;text-align:left;vertical-align:top}th{font-size:12px;color:#657064;background:#fafbf8;position:sticky;top:0}td{font-size:14px}code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}code{background:#eef1ec;padding:2px 5px;border-radius:4px;word-break:break-all}.json-block{background:#101713;color:#e8eee7;border-radius:8px;padding:12px;overflow:auto;max-height:420px}.badge{display:inline-flex;align-items:center;border-radius:999px;background:#edf1eb;color:#2f3b34;padding:3px 8px;font-size:12px;font-weight:700}.status-completed{background:#dff3df;color:#145c25}.status-failed{background:#ffe0dc;color:#8a1f12}.status-running{background:#dde9ff;color:#173d84}.detail-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;background:white;border:1px solid #dfe3dc;border-radius:8px;padding:14px;margin-bottom:12px}.artifact-list,.report-grid{display:grid;gap:12px}.artifact-row{display:grid;grid-template-columns:auto minmax(120px,240px) minmax(0,1fr);gap:10px;align-items:center}.report-card{display:grid;grid-template-columns:minmax(180px,260px) minmax(0,1fr);gap:14px}@media(max-width:760px){body{display:block}aside{position:static;height:auto;padding:14px}nav{display:flex;overflow:auto;margin-top:12px}nav a{white-space:nowrap}main{padding:16px}h1{font-size:23px}.detail-head,.report-card,.artifact-row{display:block}.artifact-row>*{display:block;margin:6px 0}table{min-width:620px}}"
}

fn json_block(title: &str, value: &Value) -> String {
    if value.is_null() {
        return String::new();
    }
    format!(
        "<h2>{}</h2><pre>{}</pre>",
        escape(title),
        escape(&serde_json::to_string_pretty(value).unwrap_or_default())
    )
}

fn read_json(path: &Path) -> RlabResult<Value> {
    if !path.is_file() {
        return Ok(Value::Null);
    }
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    serde_json::from_str(&text).map_err(RlabError::serialization)
}

fn decode_query(value: &str) -> String {
    value
        .replace("%3A", ":")
        .replace("%3a", ":")
        .replace("%2F", "/")
        .replace("%2f", "/")
        .replace("%40", "@")
}

fn escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn open_url(url: &str) {
    let mut command = if cfg!(target_os = "macos") {
        let mut command = std::process::Command::new("open");
        command.arg(url);
        command
    } else if cfg!(target_os = "windows") {
        let mut command = std::process::Command::new("cmd");
        command.arg("/C").arg("start").arg(url);
        command
    } else {
        let mut command = std::process::Command::new("xdg-open");
        command.arg(url);
        command
    };
    let _ = command.status();
}
