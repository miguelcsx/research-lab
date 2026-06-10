use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    run::{list_runs, show_run},
    RlabResult,
};

use crate::render::{
    human::{print_line, print_runs},
    json::print_json,
};

#[derive(Debug, Args)]
pub struct RunsCommand {
    #[command(subcommand)]
    pub command: RunsSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum RunsSubcommand {
    List,
    Show { id: String },
}

pub fn run(command: RunsCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        RunsSubcommand::List => {
            let runs = list_runs(&paths)?;
            if json {
                print_json("runs_list", &runs)?;
            } else {
                print_runs(&runs)?;
            }
        }
        RunsSubcommand::Show { id } => {
            let run = show_run(&paths, &id)?;
            if json {
                print_json("run_show", run)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&run)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
    }
    Ok(0)
}
