use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ErrorsCommand {
    pub run_id: String,
}

pub fn run(command: ErrorsCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let report = rlab_core::render_run_error(&paths, &command.run_id)?;
    if json {
        print_json("errors", report)?;
    } else {
        print_line(&report.error);
    }
    Ok(0)
}
