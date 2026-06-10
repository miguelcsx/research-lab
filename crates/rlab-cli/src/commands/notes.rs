use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct NotesCommand {
    #[command(subcommand)]
    pub command: NotesSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum NotesSubcommand {
    Add { run_id: String, text: String },
    List { run_id: String },
}

pub fn run(command: NotesCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        NotesSubcommand::Add { run_id, text } => {
            let entry = rlab_core::add_run_note(&paths, &run_id, &text)?;
            if json {
                print_json("notes_add", entry)?;
            } else {
                print_line("note added");
            }
        }
        NotesSubcommand::List { run_id } => {
            let notes = rlab_core::list_run_notes(&paths, &run_id)?;
            if json {
                print_json("notes_list", notes)?;
            } else {
                for note in notes {
                    print_line(&note.text);
                }
            }
        }
    }
    Ok(0)
}
