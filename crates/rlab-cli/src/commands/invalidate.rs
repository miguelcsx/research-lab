use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, fs::append_line, load_effective_config, RlabResult};
use serde_json::json;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct InvalidateCommand {
    pub reference: String,
    #[arg(long)]
    pub reason: String,
    #[arg(long)]
    pub by: Option<String>,
}

pub fn run(command: InvalidateCommand, root: Option<&Path>, json_output: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let event = json!({"schema_version":1,"event":"invalidate","subject":command.reference,"actor":command.by,"reason":command.reason});
    append_line(&paths.cache.join("audit.jsonl"), &event.to_string())?;
    if json_output {
        print_json("invalidate", event)?;
    } else {
        print_line("reference invalidated");
    }
    Ok(0)
}
