use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    adapter_inventory,
    host::validate_event,
    load_effective_config,
    HostCommand,
    HostEvent,
    HostRequest,
    ProtocolVersion,
    Registry,
    RlabResult,
};

use crate::host::process::run_python_host;
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
            let adapter = inventory.adapters.into_iter().find(|adapter| adapter.descriptor.name == name);
            match adapter {
                Some(value) if json => print_json("adapter_inspect", value)?,
                Some(value) => print_line(&serde_json::to_string_pretty(&value).map_err(rlab_core::RlabError::serialization)?),
                None if json => print_json("adapter_inspect", serde_json::json!({"schema_version":1,"found":false,"name":name}))?,
                None => print_line(&format!("adapter not found: {name}")),
            }
        }
    }
    Ok(0)
}

fn discover_registry(config: &rlab_core::EffectiveConfig) -> RlabResult<Registry> {
    let request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: "adapters".to_string(),
        command: HostCommand::Discover,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: None,
        run_id: None,
        params: serde_json::json!({}),
        seed: None,
        strict: config.production.strict,
        environment: serde_json::json!({}),
    };
    let events = run_python_host(&config.python.executable, &config.python.runner_module, &request)?;
    let mut registry = Registry::new();
    for event in events {
        validate_event(&event)?;
        if let HostEvent::RegistryRecord(value) = event {
            registry.insert(value.record)?;
        }
    }
    Ok(registry)
}
