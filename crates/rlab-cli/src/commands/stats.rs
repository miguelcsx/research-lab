use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::RlabResult;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct StatsCommand {
    #[command(subcommand)]
    pub command: StatsSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum StatsSubcommand {
    Compare {
        left: Vec<f64>,
        #[arg(long)]
        right: Vec<f64>,
    },
}

pub fn run(command: StatsCommand, _root: Option<&Path>, json: bool) -> RlabResult<u8> {
    match command.command {
        StatsSubcommand::Compare { left, right } => {
            let result = rlab_core::compare_metric_arrays(&left, &right)?;
            if json {
                print_json("stats_compare", result)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&result)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
    }
    Ok(0)
}
