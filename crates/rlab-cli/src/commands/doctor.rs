use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, doctor_project, load_effective_config, RlabResult};

use crate::render::{human::print_findings, json::print_json};

#[derive(Debug, Args)]
pub struct DoctorCommand {
    #[arg(long)]
    pub strict: bool,
}

pub fn run(_command: DoctorCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let findings = doctor_project(&config, &paths)?;
    if json {
        print_json("doctor", findings)?;
    } else {
        print_findings(&findings);
    }
    Ok(0)
}
