use std::path::{Path, PathBuf};

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ReportCommand {
    #[command(subcommand)]
    pub command: ReportSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum ReportSubcommand {
    Run {
        run_id: String,
        #[arg(long)]
        output: PathBuf,
    },
    Compare {
        runs: PathBuf,
        #[arg(long)]
        output: PathBuf,
    },
}

pub fn run(command: ReportCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        ReportSubcommand::Run { run_id, output } => {
            rlab_core::write_run_report(&paths, &run_id, &output)?;
            if json {
                print_json("report_run", output.display().to_string())?;
            } else {
                print_line(&format!("wrote {}", output.display()));
            }
        }
        ReportSubcommand::Compare { runs: _, output } => {
            rlab_core::write_compare_report(&paths, &output)?;
            if json {
                print_json("report_compare", output.display().to_string())?;
            } else {
                print_line(&format!("wrote {}", output.display()));
            }
        }
    }
    Ok(0)
}
