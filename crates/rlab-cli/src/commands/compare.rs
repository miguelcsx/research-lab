use std::path::Path;

use clap::Args;
use rlab_core::{compare_runs, config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct CompareCommand {
    #[arg(long)]
    pub metric: Option<String>,
}

pub fn run(command: CompareCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let rows = compare_runs(&paths, command.metric)?;
    if json {
        print_json("compare", rows)?;
    } else {
        for row in rows {
            print_line(&format!("{} {:?}", row.run_id, row.metrics));
        }
    }
    Ok(0)
}
