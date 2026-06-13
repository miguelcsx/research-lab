use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, jobs::start_job, load_effective_config, RlabResult, RunDirectory,
    RunSession,
};
use serde_json::Value;

use crate::render::{human::print_line, json::print_json};

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct ExecCommand {
    #[arg(long)]
    pub name: String,

    pub command: Vec<String>,
}

pub fn run(command: ExecCommand, root: Option<&Path>, json_output: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;

    let command_text = command_text(&command.command);
    let session = create_exec_session(&paths, &command.name, &command_text)?;

    let job = start_job(&paths, &command_text)?;
    let run = session.complete(exec_result(job))?;

    report_exec(&run, json_output)?;

    Ok(0)
}

fn create_exec_session(
    paths: &ProjectPaths,
    name: &str,
    command_text: &str,
) -> RlabResult<RunSession> {
    RunSession::create(
        paths,
        "exec",
        name,
        exec_args(command_text),
        exec_params(command_text),
    )
}

fn command_text(command: &[String]) -> String {
    command.join(" ")
}

fn exec_args(command_text: &str) -> Vec<String> {
    vec![
        "rlab".to_string(),
        "exec".to_string(),
        command_text.to_string(),
    ]
}

fn exec_params(command_text: &str) -> Value {
    let mut object = serde_json::Map::with_capacity(1);
    object.insert(
        "command".to_string(),
        Value::String(command_text.to_string()),
    );
    Value::Object(object)
}

fn exec_result(job: impl serde::Serialize) -> Value {
    serde_json::json!({
        "schema_version": SCHEMA_VERSION,
        "job": job
    })
}

fn report_exec(run: &RunDirectory, json_output: bool) -> RlabResult<()> {
    if json_output {
        print_json("exec", run)?;
    } else {
        print_line(&format!("exec run completed: {}", run.id.as_str()));
    }

    Ok(())
}
