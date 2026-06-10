use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ConfigCommand {
    #[command(subcommand)]
    pub command: ConfigSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum ConfigSubcommand {
    Show,
    Paths,
}

pub fn run(command: ConfigCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    match command.command {
        ConfigSubcommand::Show => {
            if json {
                print_json("config", config)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&config)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
        ConfigSubcommand::Paths => {
            let paths = ProjectPaths::from_config(&config)?;
            if json {
                print_json("config_paths", paths)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&paths)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
    }
    Ok(0)
}
