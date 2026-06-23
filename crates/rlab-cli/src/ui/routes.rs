use askama::Template;
use rlab_core::{config::ProjectPaths, RlabError, RlabResult};

use super::{templates, views};

const APP_CSS: &str = include_str!("static/app.css");
const APP_JS: &str = include_str!("static/app.js");

pub struct UiResponse {
    pub status: u16,
    pub content_type: &'static str,
    pub body: Vec<u8>,
}

impl UiResponse {
    fn html(status: u16, body: String) -> Self {
        Self {
            status,
            content_type: "text/html; charset=utf-8",
            body: body.into_bytes(),
        }
    }

    fn json(body: String) -> Self {
        Self {
            status: 200,
            content_type: "application/json; charset=utf-8",
            body: body.into_bytes(),
        }
    }

    fn asset(content_type: &'static str, body: &'static str) -> Self {
        Self {
            status: 200,
            content_type,
            body: body.as_bytes().to_vec(),
        }
    }

    fn empty(status: u16) -> Self {
        Self {
            status,
            content_type: "text/plain; charset=utf-8",
            body: Vec::new(),
        }
    }
}

pub fn dispatch(paths: &ProjectPaths, url: &str) -> RlabResult<UiResponse> {
    let (path, query) = split_url(url);
    match path {
        "/" | "/runs" => render(templates::RunsTemplate {
            title: "Runs",
            active: "runs",
            view: views::runs_view(paths)?,
        }),
        path if path.starts_with("/run/") => {
            let id = decode(path.trim_start_matches("/run/"));
            render(templates::RunTemplate {
                title: "Run Detail",
                active: "runs",
                view: views::run_detail_view(paths, &id)?,
            })
        }
        "/artifacts" => render(templates::ArtifactsTemplate {
            title: "Artifacts",
            active: "artifacts",
            view: views::artifacts_view(paths)?,
        }),
        "/artifact" => {
            let reference = query_value(query, "ref").ok_or_else(|| RlabError::Validation {
                message: "artifact route requires ref=<artifact-ref>".to_string(),
            })?;
            render(templates::ArtifactTemplate {
                title: "Artifact Detail",
                active: "artifacts",
                view: views::artifact_detail_view(paths, &reference)?,
            })
        }
        "/reports" => render(templates::ReportsTemplate {
            title: "Reports",
            active: "reports",
            view: views::reports_view(paths)?,
        }),
        "/report" => {
            let run = query_value(query, "run").ok_or_else(|| RlabError::Validation {
                message: "report route requires run=<id>".to_string(),
            })?;
            let name = query_value(query, "name").ok_or_else(|| RlabError::Validation {
                message: "report route requires name=<report>".to_string(),
            })?;
            render(templates::ReportTemplate {
                title: "Report",
                active: "reports",
                view: views::report_detail_view(paths, &run, &name)?,
            })
        }
        "/tables" => render(templates::SectionsTemplate {
            title: "Tables",
            active: "tables",
            view: views::sections_view(paths, "table")?,
        }),
        "/figures" => render(templates::SectionsTemplate {
            title: "Figures",
            active: "figures",
            view: views::sections_view(paths, "figure")?,
        }),
        "/compare" => {
            let run_ids = query_value(query, "runs")
                .map(|value| {
                    value
                        .split(',')
                        .map(str::trim)
                        .filter(|item| !item.is_empty())
                        .map(str::to_string)
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            render(templates::CompareTemplate {
                title: "Compare",
                active: "compare",
                view: views::compare_view(paths, &run_ids)?,
            })
        }
        "/api/runs" => json(&views::runs_view(paths)?),
        path if path.starts_with("/api/run/") => {
            let id = decode(path.trim_start_matches("/api/run/"));
            json(&views::run_detail_view(paths, &id)?)
        }
        "/api/artifacts" => json(&views::artifacts_view(paths)?),
        "/api/reports" => json(&views::reports_view(paths)?),
        "/api/sections" => {
            let kind = query_value(query, "type").unwrap_or_else(|| "table".to_string());
            json(&views::sections_view(paths, &kind)?)
        }
        "/static/app.css" => Ok(UiResponse::asset("text/css; charset=utf-8", APP_CSS)),
        "/static/app.js" => Ok(UiResponse::asset(
            "application/javascript; charset=utf-8",
            APP_JS,
        )),
        "/favicon.ico" => Ok(UiResponse::empty(204)),
        _ => render_status(
            404,
            templates::ErrorTemplate {
                title: "Not Found",
                active: "",
                message: "Unknown rlab UI route.".to_string(),
            },
        ),
    }
}

fn render<T: Template>(template: T) -> RlabResult<UiResponse> {
    render_status(200, template)
}

fn render_status<T: Template>(status: u16, template: T) -> RlabResult<UiResponse> {
    template
        .render()
        .map(|body| UiResponse::html(status, body))
        .map_err(RlabError::serialization)
}

fn json<T: serde::Serialize>(value: &T) -> RlabResult<UiResponse> {
    serde_json::to_string(value)
        .map(UiResponse::json)
        .map_err(RlabError::serialization)
}

fn split_url(url: &str) -> (&str, &str) {
    url.split_once('?').unwrap_or((url, ""))
}

fn query_value(query: &str, key: &str) -> Option<String> {
    query.split('&').find_map(|part| {
        let (left, right) = part.split_once('=')?;
        (left == key).then(|| decode(right))
    })
}

fn decode(value: &str) -> String {
    let bytes = value.as_bytes();
    let mut output = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'%' if index + 2 < bytes.len() => {
                let hi = hex(bytes[index + 1]);
                let lo = hex(bytes[index + 2]);
                if let (Some(hi), Some(lo)) = (hi, lo) {
                    output.push((hi << 4) | lo);
                    index += 3;
                } else {
                    output.push(bytes[index]);
                    index += 1;
                }
            }
            b'+' => {
                output.push(b' ');
                index += 1;
            }
            byte => {
                output.push(byte);
                index += 1;
            }
        }
    }
    String::from_utf8_lossy(&output).to_string()
}

fn hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_routes_are_404() {
        let paths = ProjectPaths {
            root: std::env::temp_dir(),
            runs: std::env::temp_dir(),
            cache: std::env::temp_dir(),
            artifacts: std::env::temp_dir(),
            registry_cache: std::env::temp_dir(),
        };
        let response = dispatch(&paths, "/missing").expect("route should render");
        assert_eq!(response.status, 404);
    }

    #[test]
    fn static_assets_have_content_types() {
        let paths = ProjectPaths {
            root: std::env::temp_dir(),
            runs: std::env::temp_dir(),
            cache: std::env::temp_dir(),
            artifacts: std::env::temp_dir(),
            registry_cache: std::env::temp_dir(),
        };
        let response = dispatch(&paths, "/static/app.css").expect("asset should render");
        assert_eq!(response.content_type, "text/css; charset=utf-8");
    }
}
