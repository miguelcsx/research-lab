use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct GcCommand {
    #[arg(long)]
    pub dry_run: bool,
    #[arg(long)]
    pub force: bool,
    #[arg(long)]
    pub materialized_only: bool,
    #[arg(long)]
    pub prune_runs: bool,
    #[arg(long)]
    pub older_than: Option<String>,
}

pub fn run(command: GcCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    if !command.prune_runs && command.older_than.is_some() {
        return Err(rlab_core::RlabError::validation(
            "gc --older-than is only valid with --prune-runs",
        ));
    }
    if !command.dry_run && !command.force {
        return Err(rlab_core::RlabError::validation(
            "gc requires --dry-run or --force",
        ));
    }
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let summary = if command.prune_runs {
        let raw = command.older_than.as_deref().ok_or_else(|| {
            rlab_core::RlabError::validation("gc --prune-runs requires --older-than")
        })?;
        rlab_core::prune_runs(&paths, command.dry_run, parse_duration(raw)?)?
    } else {
        rlab_core::gc_artifacts(&paths, command.dry_run, command.materialized_only)?
    };
    if json {
        print_json("gc", summary)?;
    } else if summary.dry_run {
        print_line(&format!(
            "would remove {} files, {} dirs, {} bytes",
            summary.removed_files, summary.removed_dirs, summary.removed_bytes
        ));
    } else {
        print_line(&format!(
            "removed {} files, {} dirs, {} bytes",
            summary.removed_files, summary.removed_dirs, summary.removed_bytes
        ));
    }
    Ok(0)
}

fn parse_duration(value: &str) -> rlab_core::RlabResult<std::time::Duration> {
    let trimmed = value.trim();
    if trimmed.len() < 2 {
        return Err(rlab_core::RlabError::validation(
            "duration must look like 7d, 24h, or 60m",
        ));
    }
    let (number, unit) = trimmed.split_at(trimmed.len() - 1);
    let amount: u64 = number.parse().map_err(|_| {
        rlab_core::RlabError::validation("duration amount must be a positive integer")
    })?;
    let seconds = match unit {
        "d" => amount * 24 * 60 * 60,
        "h" => amount * 60 * 60,
        "m" => amount * 60,
        "s" => amount,
        _ => {
            return Err(rlab_core::RlabError::validation(
                "duration unit must be d, h, m, or s",
            ))
        }
    };
    Ok(std::time::Duration::from_secs(seconds))
}
