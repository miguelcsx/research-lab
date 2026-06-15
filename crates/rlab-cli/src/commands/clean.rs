use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct CleanCommand {
    #[arg(long)]
    pub force: bool,
}

pub fn run(command: CleanCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let summary = rlab_core::clean_project_state(&paths, command.force)?;

    if json {
        print_json("clean", summary)?;
    } else if summary.removed {
        print_line(&format!("removed {}", summary.path));
    } else {
        print_line(&format!(
            "would remove {} ({} files, {} bytes); pass --force to clean",
            summary.path, summary.before_files, summary.before_bytes
        ));
    }

    Ok(0)
}
