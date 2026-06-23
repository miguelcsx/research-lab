use std::fs;
use std::path::{Path, PathBuf};

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, load_effective_config, resolve_path_reference, run::inspect_run,
    ArtifactStore, RlabError, RlabResult,
};
use serde_json::{json, Value};

use crate::render::{
    human::{accent, dim, kind_badge, path as styled_path, print_line, section, status, target},
    json::print_json,
};

#[derive(Debug, Args)]
pub struct ViewCommand {
    #[command(subcommand)]
    pub command: ViewSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum ViewSubcommand {
    Run { reference: String },
    Artifact { reference: String },
    Report { reference: String },
}

pub fn run(command: ViewCommand, root: Option<&Path>, as_json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        ViewSubcommand::Run { reference } => view_run(&paths, &reference, as_json)?,
        ViewSubcommand::Artifact { reference } => view_artifact(&paths, &reference, as_json)?,
        ViewSubcommand::Report { reference } => view_report(&paths, &reference, as_json)?,
    }
    Ok(0)
}

fn view_run(paths: &ProjectPaths, reference: &str, as_json: bool) -> RlabResult<()> {
    let id = run_id_from_reference(paths, reference)?;
    let details = inspect_run(paths, &id)?;
    if as_json {
        return print_json("view_run", &details);
    }
    print_line(&format!(
        "{} {}",
        accent("rlab view run"),
        target(details.run.id.as_str())
    ));
    print_line(&format!(
        "  {} {}:{}  {}",
        dim("target"),
        kind_badge(&details.run.operation),
        details.run.name,
        status(details.run.status.as_str())
    ));
    print_line(&format!(
        "  {} {}",
        dim("path"),
        styled_path(&details.run.path.display().to_string())
    ));
    print_line(&format!(
        "  {} rlab open run {}",
        dim("open"),
        details.run.id.as_str()
    ));
    if let Some(params) = read_json(&details.run.path.join("params.json"))?.as_object() {
        if !params.is_empty() {
            print_line("");
            print_line(&section("params"));
            for (key, value) in params {
                print_line(&format!("  {} {}", dim(key), value));
            }
        }
    }
    if let Some(metrics) = details
        .metrics
        .as_object()
        .filter(|value| !value.is_empty())
    {
        print_line("");
        print_line(&section("metrics"));
        for (key, value) in metrics {
            print_line(&format!("  {} {}", dim(key), value));
        }
    }
    if !details.artifacts.is_empty() {
        print_line("");
        print_line(&section("artifacts"));
        for artifact in &details.artifacts {
            let name = artifact
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or("artifact");
            let kind = artifact
                .get("kind")
                .and_then(Value::as_str)
                .unwrap_or("file");
            let artifact_target = artifact
                .get("artifact_ref")
                .or_else(|| artifact.get("path"))
                .or_else(|| artifact.get("object_path"))
                .and_then(Value::as_str)
                .unwrap_or("");
            print_line(&format!("  {} {}", kind_badge(kind), target(name)));
            if !artifact_target.is_empty() {
                print_line(&format!(
                    "      {} {}",
                    dim("path"),
                    styled_path(artifact_target)
                ));
            }
            if kind == "report" {
                print_line(&format!(
                    "      {} rlab view report {}",
                    dim("view"),
                    details.run.id.as_str()
                ));
                print_line(&format!(
                    "      {} rlab open report {}",
                    dim("open"),
                    details.run.id.as_str()
                ));
            } else if !artifact_target.is_empty() {
                print_line(&format!(
                    "      {} rlab open artifact {artifact_target}",
                    dim("open")
                ));
            }
        }
    }
    if let Some(error) = details.error.filter(|value| !value.trim().is_empty()) {
        print_line("");
        print_line(&section("error"));
        print_line(&error);
    }
    Ok(())
}

fn view_artifact(paths: &ProjectPaths, reference: &str, as_json: bool) -> RlabResult<()> {
    let manifest = ArtifactStore::new(paths).describe(reference)?;
    if as_json {
        return print_json("view_artifact", &manifest);
    }
    print_line(&format!(
        "{} {}",
        accent("rlab view artifact"),
        target(reference)
    ));
    print_line(&serde_json::to_string_pretty(&manifest).map_err(RlabError::serialization)?);
    print_line(&format!("\n{} rlab artifact path {reference}", dim("path")));
    print_line(&format!("{} rlab open artifact {reference}", dim("open")));
    Ok(())
}

fn view_report(paths: &ProjectPaths, reference: &str, as_json: bool) -> RlabResult<()> {
    let path = report_path(paths, reference)?;
    let manifest = read_json(&path.join("report_manifest.json"))?;
    if as_json {
        return print_json("view_report", json!({"path": path, "manifest": manifest}));
    }
    print_line(&format!(
        "{} {}",
        accent("rlab view report"),
        styled_path(&path.display().to_string())
    ));
    if manifest.is_null() {
        print_line(&dim("no report_manifest.json found"));
        return Ok(());
    }
    let name = manifest
        .get("name")
        .and_then(Value::as_str)
        .unwrap_or("report");
    print_line(&format!("  {} {}", dim("name"), target(name)));
    if let Some(metrics) = manifest.get("metrics").and_then(Value::as_object) {
        if !metrics.is_empty() {
            print_line("");
            print_line(&section("metrics"));
            for (key, value) in metrics {
                print_line(&format!("  {} {}", dim(key), value));
            }
        }
    }
    if let Some(sections) = manifest.get("sections").and_then(Value::as_array) {
        print_line("");
        print_line(&section("sections"));
        for section in sections {
            let kind = section
                .get("type")
                .and_then(Value::as_str)
                .unwrap_or("section");
            let name = section.get("name").and_then(Value::as_str).unwrap_or(kind);
            let path = section.get("path").and_then(Value::as_str).unwrap_or("");
            print_line(&format!(
                "  {} {}  {} {}",
                kind_badge(kind),
                target(name),
                dim("path"),
                styled_path(path)
            ));
        }
    }
    print_line(&format!("\n{} rlab open report {reference}", dim("open")));
    Ok(())
}

fn run_id_from_reference(paths: &ProjectPaths, reference: &str) -> RlabResult<String> {
    if let Some(id) = reference.strip_prefix("run:") {
        return Ok(id.to_string());
    }
    if reference.starts_with('@') {
        let path = resolve_path_reference(paths, reference)?;
        return path
            .file_name()
            .map(|value| value.to_string_lossy().to_string())
            .ok_or_else(|| RlabError::Validation {
                message: format!("could not resolve run id from {reference}"),
            });
    }
    Ok(reference.to_string())
}

fn report_path(paths: &ProjectPaths, reference: &str) -> RlabResult<PathBuf> {
    if reference.starts_with("artifact:") {
        return ArtifactStore::new(paths).resolve_path(reference);
    }
    if reference.starts_with('@') && reference.contains('/') {
        return resolve_path_reference(paths, reference);
    }
    let id = run_id_from_reference(paths, reference)?;
    let details = inspect_run(paths, &id)?;
    for artifact in &details.artifacts {
        if artifact.get("kind").and_then(Value::as_str) == Some("report") {
            if let Some(path) = artifact
                .get("path")
                .or_else(|| artifact.get("object_path"))
                .and_then(Value::as_str)
            {
                return Ok(PathBuf::from(path));
            }
        }
    }
    Ok(details.run.path.join("outputs").join("reports"))
}

fn read_json(path: &Path) -> RlabResult<Value> {
    if !path.is_file() {
        return Ok(Value::Null);
    }
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    serde_json::from_str(&text).map_err(RlabError::serialization)
}
