use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{adapter_inventory, load_effective_config, Registry, RlabResult};

use crate::host::execution;
use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct AdaptersCommand {
    #[command(subcommand)]
    pub command: AdaptersSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum AdaptersSubcommand {
    List,
    Inspect { name: String },
}

pub fn run(command: AdaptersCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let registry = discover_registry(&config)?;
    let inventory = adapter_inventory(&registry)?;
    match command.command {
        AdaptersSubcommand::List => {
            if json {
                print_json("adapters_list", inventory)?;
            } else {
                for adapter in inventory.adapters {
                    print_line(&format!("{} {:?}", adapter.descriptor.name, adapter.status));
                }
            }
        }
        AdaptersSubcommand::Inspect { name } => {
            let adapter = inventory
                .adapters
                .into_iter()
                .find(|adapter| adapter.descriptor.name == name);
            match adapter {
                Some(value) if json => print_json("adapter_inspect", value)?,
                Some(value) => print_line(
                    &serde_json::to_string_pretty(&value)
                        .map_err(rlab_core::RlabError::serialization)?,
                ),
                None if json => print_json(
                    "adapter_inspect",
                    serde_json::json!({"schema_version":1,"found":false,"name":name}),
                )?,
                None => print_line(&format!("adapter not found: {name}")),
            }
        }
    }
    Ok(0)
}

fn discover_registry(config: &rlab_core::EffectiveConfig) -> RlabResult<Registry> {
    execution::discover_registry(config, config.production.strict)
}
