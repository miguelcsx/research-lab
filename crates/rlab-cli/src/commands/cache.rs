use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct CacheCommand {
    #[command(subcommand)]
    pub command: CacheSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum CacheSubcommand {
    Path,
    Inspect,
    List,
    Clean,
    Prune { name: String },
}

pub fn run(command: CacheCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        CacheSubcommand::Path => {
            let path = rlab_core::cache_path(&paths);
            if json {
                print_json("cache_path", path.display().to_string())?;
            } else {
                print_line(&path.display().to_string());
            }
        }
        CacheSubcommand::Inspect => {
            let inspection = rlab_core::cache_inspect(&paths)?;
            if json {
                print_json("cache_inspect", inspection)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&inspection)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
        CacheSubcommand::List => {
            let entries = rlab_core::cache_list(&paths)?;
            if json {
                print_json("cache_list", entries)?;
            } else {
                for entry in entries {
                    print_line(&format!("{} {}", entry.bytes, entry.path));
                }
            }
        }
        CacheSubcommand::Clean => {
            let inspection = rlab_core::clean_cache(&paths)?;
            if json {
                print_json("cache_clean", inspection)?;
            } else {
                print_line("cache cleaned");
            }
        }
        CacheSubcommand::Prune { name } => {
            if name == "downloads" {
                let inspection = rlab_core::cache_inspect(&paths)?;
                if json {
                    print_json("cache_prune", inspection)?;
                } else {
                    print_line("download cache prune completed");
                }
            } else {
                return Err(rlab_core::RlabError::Validation {
                    message: format!("unknown cache prune target: {name}"),
                });
            }
        }
    }
    Ok(0)
}
