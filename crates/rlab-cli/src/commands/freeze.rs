use std::fs;
use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths,
    fs::{ensure_dir, write_text_atomic},
    load_effective_config, RlabError, RlabResult,
};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct FreezeCommand {
    #[command(subcommand)]
    pub command: FreezeSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum FreezeSubcommand {
    Run {
        run_id: String,
        #[arg(long)]
        r#as: String,
    },
    Lock {
        run_id: String,
    },
}

pub fn run(command: FreezeCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        FreezeSubcommand::Run { run_id, r#as } => {
            let source = paths.runs.join(&run_id);
            if !source.is_dir() {
                return Err(RlabError::NotFound {
                    subject: format!("run {run_id}"),
                });
            }
            let target = paths.root.join("paper").join(&r#as).join(&run_id);
            copy_dir_recursive(&source, &target)?;
            write_text_atomic(&target.join("frozen.txt"), "frozen by rlab\n")?;
            if json {
                print_json(
                    "freeze_run",
                    serde_json::json!({"run_id": run_id, "label": r#as, "path": target}),
                )?;
            } else {
                print_line(&format!(
                    "frozen run {run_id} as {as_label}",
                    as_label = r#as
                ));
            }
        }
        FreezeSubcommand::Lock { run_id } => {
            let run_dir = paths.runs.join(&run_id);
            if !run_dir.is_dir() {
                return Err(RlabError::NotFound {
                    subject: format!("run {run_id}"),
                });
            }
            write_text_atomic(&run_dir.join(".locked"), "locked by rlab\n")?;
            if json {
                print_json(
                    "freeze_lock",
                    serde_json::json!({"run_id": run_id, "locked": true}),
                )?;
            } else {
                print_line(&format!("locked run {run_id}"));
            }
        }
    }
    Ok(0)
}

fn copy_dir_recursive(source: &Path, target: &Path) -> RlabResult<()> {
    ensure_dir(target)?;
    let entries = fs::read_dir(source).map_err(|error| RlabError::io(source, error))?;
    for entry in entries {
        let entry = entry.map_err(|error| RlabError::io(source, error))?;
        let entry_path = entry.path();
        let target_path = target.join(entry.file_name());
        if entry_path.is_dir() {
            copy_dir_recursive(&entry_path, &target_path)?;
        } else {
            fs::copy(&entry_path, &target_path)
                .map_err(|error| RlabError::io(&target_path, error))?;
        }
    }
    Ok(())
}
