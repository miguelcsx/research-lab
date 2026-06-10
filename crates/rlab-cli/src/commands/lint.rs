use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct LintCommand {}

pub fn run(_command: LintCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let findings = rlab_core::lint_project(&paths)?;
    if json {
        print_json("lint", findings)?;
    } else {
        for finding in findings {
            print_line(&format!("{}: {}", finding.level, finding.message));
        }
    }
    Ok(0)
}
