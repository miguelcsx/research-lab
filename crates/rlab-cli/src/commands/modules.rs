use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    diagnose_modules, list_modules, load_effective_config, reload_modules_plan, RlabResult,
};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ModulesCommand {
    #[command(subcommand)]
    pub command: ModulesSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum ModulesSubcommand {
    List,
    Doctor,
    Reload,
}

pub fn run(command: ModulesCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    match command.command {
        ModulesSubcommand::List => {
            let modules = list_modules(&config);
            if json {
                print_json("modules_list", modules)?;
            } else {
                for module in modules {
                    print_line(&module.name);
                }
            }
        }
        ModulesSubcommand::Doctor => {
            let diagnostics = diagnose_modules(&config);
            if json {
                print_json("modules_doctor", diagnostics)?;
            } else {
                for diagnostic in diagnostics {
                    print_line(&format!(
                        "{:?} {}: {}",
                        diagnostic.level, diagnostic.module, diagnostic.message
                    ));
                }
            }
        }
        ModulesSubcommand::Reload => {
            let plan = reload_modules_plan(&config);
            if json {
                print_json("modules_reload", plan)?;
            } else {
                print_line(&format!(
                    "would reload {} modules and purge registry cache",
                    plan.modules.len()
                ));
            }
        }
    }
    Ok(0)
}
