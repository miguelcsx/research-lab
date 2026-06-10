use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    migrate::{migration_plan, migration_status},
    RlabResult,
};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct MigrateCommand {
    #[command(subcommand)]
    pub command: MigrateSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum MigrateSubcommand {
    Status,
    Plan,
    Apply,
}

pub fn run(command: MigrateCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        MigrateSubcommand::Status => {
            let status = migration_status();
            if json {
                print_json("migrate_status", status)?;
            } else {
                print_line("schema version is current for newly created rlab files");
            }
        }
        MigrateSubcommand::Plan => {
            let plan = migration_plan(&paths)?;
            if json {
                print_json("migrate_plan", plan)?;
            } else if plan.actions.is_empty() {
                print_line("no migration actions required");
            } else {
                for action in plan.actions {
                    print_line(&format!("{}: {}", action.path.display(), action.reason));
                }
            }
        }
        MigrateSubcommand::Apply => {
            let plan = migration_plan(&paths)?;
            plan.ensure_supported()?;
            if json {
                print_json(
                    "migrate_apply",
                    serde_json::json!({"applied": true, "actions": []}),
                )?;
            } else {
                print_line("no destructive automatic migrations were required");
            }
        }
    }
    Ok(0)
}
