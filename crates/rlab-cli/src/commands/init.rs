use std::path::Path;

use clap::Args;
use rlab_core::{load_effective_config, template::init_project, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct InitCommand {
    #[arg(default_value = "")]
    pub name: String,
}

pub fn run(command: InitCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let name = if command.name.trim().is_empty() { config.project.name.clone() } else { command.name };
    init_project(&config.project.root, &name)?;
    if json {
        print_json("init", serde_json::json!({"project": name, "root": config.project.root}))?;
    } else {
        print_line(&format!("initialized rlab project '{name}'"));
    }
    Ok(0)
}
