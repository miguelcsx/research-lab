use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    run::{inspect_run, list_runs},
    RlabResult,
};
use serde_json::Value;

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
        RunsSubcommand::List => render(json, "runs_list", list_runs(&paths)?, |runs| {
            print_runs(runs)
        })?,
        RunsSubcommand::Show { id } => {
            render(json, "run_show", inspect_run(&paths, &id)?, |details| {
                print_run_details(details)
            })?
        }
    }

    Ok(0)
}

fn render<T, F>(json: bool, name: &str, value: T, human: F) -> RlabResult<()>
where
    T: serde::Serialize,
    F: FnOnce(&T) -> RlabResult<()>,
{
    if json {
        print_json(name, &value)
    } else {
        human(&value)
    }
}

fn print_run_details(details: &rlab_core::run::RunDetails) -> RlabResult<()> {
    print_line(&format!(
        "{}  {}  {}",
        details.run.id.as_str(),
        details.run.status.as_str(),
        details.run.path.display()
    ));

    print_object_section("metrics", details.metrics.as_object(), |name, value| {
        format!("  {name}: {value}")
    });

    if !details.results.is_null() {
        print_line("\nresults:");
        print_line(
            &serde_json::to_string_pretty(&details.results)
                .map_err(rlab_core::RlabError::serialization)?,
        );
    }

    print_items_section("artifacts", &details.artifacts, |artifact| {
        Some(format!(
            "  {}: {}",
            first_str(artifact, &["name"], "artifact"),
            first_str(artifact, &["staged_path", "path"], "")
        ))
    });

    print_items_section("logs", &details.logs, |log| {
        log.get("message")
            .and_then(Value::as_str)
            .or_else(|| log.as_str())
            .filter(|message| !message.is_empty())
            .map(|message| format!("  {message}"))
    });

    if let Some(error) = &details.error {
        print_line("\nerror:");
        print_line(&format!("  {}", error_message(error)));
        print_line(&format!(
            "  traceback: rlab errors {}",
            details.run.id.as_str()
        ));
    }

    Ok(())
}

fn print_object_section<F>(title: &str, object: Option<&serde_json::Map<String, Value>>, line: F)
where
    F: Fn(&str, &Value) -> String,
{
    if let Some(object) = object.filter(|object| !object.is_empty()) {
        print_line(&format!("\n{title}:"));
        object
            .iter()
            .for_each(|(key, value)| print_line(&line(key, value)));
    }
}

fn print_items_section<F>(title: &str, items: &[Value], line: F)
where
    F: Fn(&Value) -> Option<String>,
{
    if !items.is_empty() {
        print_line(&format!("\n{title}:"));
        items
            .iter()
            .filter_map(line)
            .for_each(|line| print_line(&line));
    }
}

fn first_str<'a>(value: &'a Value, keys: &[&str], fallback: &'a str) -> &'a str {
    keys.iter()
        .find_map(|key| value.get(*key).and_then(Value::as_str))
        .map_or(fallback, |value| value)
}

fn error_message(error: &str) -> String {
    match serde_json::from_str::<Value>(error) {
        Ok(value) => value
            .get("message")
            .and_then(Value::as_str)
            .map_or_else(|| error.to_owned(), str::to_owned),
        Err(_) => error.to_owned(),
    }
}
