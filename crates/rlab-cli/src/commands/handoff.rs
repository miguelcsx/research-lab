use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct HandoffCommand {
    pub run_id: String,
    #[arg(long)]
    pub to: String,
}

pub fn run(command: HandoffCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let path = rlab_core::write_handoff(&paths, &command.run_id, &command.to)?;
    if json {
        print_json("handoff", path.display().to_string())?;
    } else {
        print_line(&format!("wrote {}", path.display()));
    }
    Ok(0)
}
