use std::path::{Path, PathBuf};

use clap::Args;
use rlab_core::RlabResult;

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct TableCommand {
    pub path: PathBuf,
}

pub fn run(command: TableCommand, _root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let table = rlab_core::render_table(&command.path)?;
    if json {
        print_json("table", table)?;
    } else {
        print_line(&table.text);
    }
    Ok(0)
}
