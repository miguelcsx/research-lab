use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct CiCommand {
    #[command(subcommand)]
    pub command: CiSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum CiSubcommand {
    Smoke,
    Compare {
        #[arg(long)]
        metric: String,
        #[arg(long)]
        threshold: f64,
    },
    ReproducibilityCheck,
}

pub fn run(command: CiCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let result = match command.command {
        CiSubcommand::Smoke => rlab_core::ci_smoke(&config, &paths)?,
        CiSubcommand::Compare { metric, threshold } => {
            rlab_core::ci_compare(&paths, &metric, threshold)?
        }
        CiSubcommand::ReproducibilityCheck => rlab_core::ci_reproducibility_check(&paths)?,
    };
    let passed = result.passed;
    if json {
        print_json("ci", result)?;
    } else {
        print_line(&format!(
            "{}: {}",
            if passed { "passed" } else { "failed" },
            result.message
        ));
    }
    Ok(if passed { 0 } else { 1 })
}
