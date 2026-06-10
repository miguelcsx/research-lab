use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct GraphCommand {
    #[command(subcommand)]
    pub command: GraphSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum GraphSubcommand {
    Build,
    Query {
        reference: String,
    },
    Lineage {
        reference: String,
    },
    AddEdge {
        from: String,
        to: String,
        #[arg(long)]
        reason: Option<String>,
    },
}

pub fn run(command: GraphCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        GraphSubcommand::Build => {
            let report = rlab_core::lineage_for(&paths, "root")?;
            if json {
                print_json("graph_build", report)?;
            } else {
                print_line("lineage graph index ready");
            }
        }
        GraphSubcommand::Query { reference } | GraphSubcommand::Lineage { reference } => {
            let report = rlab_core::lineage_for(&paths, &reference)?;
            if json {
                print_json("graph_lineage", report)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&report)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
        GraphSubcommand::AddEdge { from, to, reason } => {
            let edge = rlab_core::add_lineage_edge(&paths, &from, &to, reason)?;
            if json {
                print_json("graph_add_edge", edge)?;
            } else {
                print_line("lineage edge added");
            }
        }
    }
    Ok(0)
}
