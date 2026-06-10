use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, jobs::start_job, load_effective_config, RlabResult, RunSession,
};
use serde_json::json;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ExecCommand {
    #[arg(long)]
    pub name: String,
    pub command: Vec<String>,
}

pub fn run(command: ExecCommand, root: Option<&Path>, json_output: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let command_text = command.command.join(" ");
    let session = RunSession::create(
        &paths,
        "exec",
        &command.name,
        vec!["rlab".to_string(), "exec".to_string(), command_text.clone()],
        json!({"command": command_text}),
    )?;
    let job = start_job(&paths, &command_text)?;
    let run = session.complete(json!({"schema_version":1,"job":job}))?;
    if json_output {
        print_json("exec", run)?;
    } else {
        print_line(&format!("exec run completed: {}", run.id.as_str()));
    }
    Ok(0)
}
