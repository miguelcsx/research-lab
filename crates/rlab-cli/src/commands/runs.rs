use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    run::{inspect_run, list_runs},
    RlabResult,
};

use crate::render::{
    human::{print_line, print_runs},
    json::print_json,
};

#[derive(Debug, Args)]
pub struct RunsCommand {
    #[command(subcommand)]
    pub command: RunsSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum RunsSubcommand {
    List,
    Show { id: String },
}

pub fn run(command: RunsCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        RunsSubcommand::List => {
            let runs = list_runs(&paths)?;
            if json {
                print_json("runs_list", &runs)?;
            } else {
                print_runs(&runs)?;
            }
        }
        RunsSubcommand::Show { id } => {
            let details = inspect_run(&paths, &id)?;
            if json {
                print_json("run_show", details)?;
            } else {
                print_run_details(&details)?;
            }
        }
    }
    Ok(0)
}

fn print_run_details(details: &rlab_core::run::RunDetails) -> RlabResult<()> {
    print_line(&format!(
        "{}  {}  {}",
        details.run.id.as_str(),
        details.run.status.as_str(),
        details.run.path.display()
    ));
    if let Some(metrics) = details.metrics.as_object() {
        if !metrics.is_empty() {
            print_line("\nmetrics:");
            for (name, value) in metrics {
                print_line(&format!("  {name}: {value}"));
            }
        }
    }
    if !details.results.is_null() {
        print_line("\nresults:");
        print_line(
            &serde_json::to_string_pretty(&details.results)
                .map_err(rlab_core::RlabError::serialization)?,
        );
    }
    if !details.artifacts.is_empty() {
        print_line("\nartifacts:");
        for artifact in &details.artifacts {
            let name = artifact
                .get("name")
                .and_then(|value| value.as_str())
                .unwrap_or("artifact");
            let path = artifact
                .get("staged_path")
                .or_else(|| artifact.get("path"))
                .and_then(|value| value.as_str())
                .unwrap_or("");
            print_line(&format!("  {name}: {path}"));
        }
    }
    if !details.logs.is_empty() {
        print_line("\nlogs:");
        for log in &details.logs {
            let message = log
                .get("message")
                .and_then(|value| value.as_str())
                .unwrap_or_else(|| log.as_str().unwrap_or(""));
            if !message.is_empty() {
                print_line(&format!("  {message}"));
            }
        }
    }
    if let Some(error) = &details.error {
        print_line("\nerror:");
        print_line(error);
    }
    Ok(())
}
