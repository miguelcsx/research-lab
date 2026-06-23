use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, load_effective_config, optimize_storage, RlabError, RlabResult,
};

use crate::render::{human::print_line, json::print_json};

/// Inspect and reclaim storage used by runs, checkpoints, and the artifact store.
#[derive(Debug, Args)]
pub struct StorageCommand {
    #[command(subcommand)]
    pub action: StorageAction,
}

#[derive(Debug, Subcommand)]
pub enum StorageAction {
    /// Apply the project's storage policy to existing runs: drop resume-only
    /// checkpoint files (optimizer state), prune runs beyond the per-experiment
    /// limit, and sweep orphaned objects. Model weights are always preserved.
    Optimize(OptimizeArgs),
}

#[derive(Debug, Args)]
pub struct OptimizeArgs {
    /// Report what would be reclaimed without modifying anything.
    #[arg(long)]
    pub dry_run: bool,
    /// Required to actually modify the store (guards against accidental runs).
    #[arg(long)]
    pub force: bool,
}

pub fn run(command: StorageCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    match command.action {
        StorageAction::Optimize(args) => optimize(args, root, json),
    }
}

fn optimize(args: OptimizeArgs, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    if !args.dry_run && !args.force {
        return Err(RlabError::validation(
            "storage optimize requires --dry-run or --force",
        ));
    }
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let summary = optimize_storage(&paths, &config.storage, args.dry_run)?;

    if json {
        print_json("storage.optimize", summary)?;
    } else {
        let verb = if summary.dry_run { "would reclaim" } else { "reclaimed" };
        let total = summary.optimizer_bytes_removed
            + summary.run_bytes_reclaimed
            + summary.object_bytes_reclaimed;
        print_line(&format!(
            "{verb} ~{:.1} GiB total\n  scanned {} completed runs\n  optimizer state: {} files across {} checkpoints ({:.1} GiB)\n  deduplicated: {} files hard-linked to the store\n  run retention: {} directories ({:.1} GiB)\n  swept objects: {} ({:.1} GiB)",
            gib(total),
            summary.runs_scanned,
            summary.optimizer_files_removed,
            summary.checkpoints_pruned,
            gib(summary.optimizer_bytes_removed),
            summary.files_relinked,
            summary.run_dirs_pruned,
            gib(summary.run_bytes_reclaimed),
            summary.objects_swept,
            gib(summary.object_bytes_reclaimed),
        ));
    }
    Ok(0)
}

fn gib(bytes: u64) -> f64 {
    bytes as f64 / 1024.0 / 1024.0 / 1024.0
}
