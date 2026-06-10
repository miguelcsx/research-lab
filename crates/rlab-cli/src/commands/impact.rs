use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ImpactCommand {
    pub reference: String,
}

pub fn run(command: ImpactCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let report = rlab_core::lineage_for(&paths, &command.reference)?;
    if json {
        print_json("impact", report)?;
    } else {
        print_line(
            &serde_json::to_string_pretty(&report).map_err(rlab_core::RlabError::serialization)?,
        );
    }
    Ok(0)
}
