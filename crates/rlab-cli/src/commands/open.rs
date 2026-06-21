use std::path::{Path, PathBuf};
use std::process::Command;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, load_effective_config, resolve_path_reference, run::inspect_run,
    ArtifactStore, RlabError, RlabResult,
};
use serde_json::Value;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct OpenCommand {
    #[command(subcommand)]
    pub command: OpenSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum OpenSubcommand {
    Run(OpenTarget),
    Artifact(OpenTarget),
    Report(OpenTarget),
    Figure(OpenTarget),
}

#[derive(Debug, Args)]
pub struct OpenTarget {
    pub reference: String,
    #[arg(long)]
    pub dry_run: bool,
}

pub fn run(command: OpenCommand, root: Option<&Path>, as_json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let target = match command.command {
        OpenSubcommand::Run(target) => (open_run_path(&paths, &target.reference)?, target.dry_run),
        OpenSubcommand::Artifact(target) | OpenSubcommand::Figure(target) => (
            ArtifactStore::new(&paths).resolve_path(&target.reference)?,
            target.dry_run,
        ),
        OpenSubcommand::Report(target) => {
            (open_report_path(&paths, &target.reference)?, target.dry_run)
        }
    };
    if as_json {
        print_json(
            "open",
            serde_json::json!({"path": target.0, "dry_run": target.1}),
        )?;
    } else {
        print_line(&format!("{}", target.0.display()));
    }
    if !target.1 {
        open_path(&target.0)?;
    }
    Ok(0)
}

fn open_run_path(paths: &ProjectPaths, reference: &str) -> RlabResult<PathBuf> {
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
    Ok(details.run.path)
}

fn open_report_path(paths: &ProjectPaths, reference: &str) -> RlabResult<PathBuf> {
    if reference.starts_with("artifact:") {
        return ArtifactStore::new(paths).resolve_path(reference);
    }
    open_run_path(paths, reference)
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

fn open_path(path: &Path) -> RlabResult<()> {
    let mut command = if cfg!(target_os = "macos") {
        let mut command = Command::new("open");
        command.arg(path);
        command
    } else if cfg!(target_os = "windows") {
        let mut command = Command::new("cmd");
        command.arg("/C").arg("start").arg(path);
        command
    } else {
        let mut command = Command::new("xdg-open");
        command.arg(path);
        command
    };
    let status = command.status().map_err(|error| RlabError::Run {
        message: format!("failed to launch opener: {error}"),
    })?;
    if status.success() {
        Ok(())
    } else {
        Err(RlabError::Run {
            message: format!("opener failed for {}", path.display()),
        })
    }
}
