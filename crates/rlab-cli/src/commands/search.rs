use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct SearchCommand {
    pub term: String,
    #[arg(long)]
    pub kind: Option<String>,
}

pub fn run(command: SearchCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let hits = rlab_core::search_project(&paths, &command.term, command.kind.as_deref())?;
    if json {
        print_json("search", hits)?;
    } else {
        for hit in hits {
            print_line(&format!("{} {} [{}]", hit.kind, hit.id, hit.score));
        }
    }
    Ok(0)
}
