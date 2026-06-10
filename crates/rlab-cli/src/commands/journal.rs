use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct JournalCommand {
    #[command(subcommand)]
    pub command: JournalSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum JournalSubcommand {
    Decision {
        #[command(subcommand)]
        command: DecisionCommand,
    },
    Negative {
        #[command(subcommand)]
        command: NegativeCommand,
    },
    Ideas {
        #[command(subcommand)]
        command: IdeasCommand,
    },
}

#[derive(Debug, Subcommand)]
pub enum DecisionCommand {
    Add {
        text: String,
        #[arg(long)]
        run: Option<String>,
    },
    List,
}
#[derive(Debug, Subcommand)]
pub enum NegativeCommand {
    Add {
        hypothesis: String,
        tried: String,
        reason: String,
    },
    List,
    Search {
        term: String,
    },
}
#[derive(Debug, Subcommand)]
pub enum IdeasCommand {
    Add { text: String },
    List,
    Promote { id: String, status: String },
}

pub fn run(command: JournalCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        JournalSubcommand::Decision { command } => match command {
            DecisionCommand::Add { text, run } => {
                let value = rlab_core::add_decision(&paths, &text, run, serde_json::json!({}))?;
                if json {
                    print_json("journal_decision_add", value)?;
                } else {
                    print_line("decision recorded");
                }
            }
            DecisionCommand::List => {
                let values = rlab_core::list_decisions(&paths)?;
                if json {
                    print_json("journal_decision_list", values)?;
                } else {
                    for value in values {
                        print_line(&value.text);
                    }
                }
            }
        },
        JournalSubcommand::Negative { command } => match command {
            NegativeCommand::Add {
                hypothesis,
                tried,
                reason,
            } => {
                let value = rlab_core::add_negative_result(&paths, &hypothesis, &tried, &reason)?;
                if json {
                    print_json("journal_negative_add", value)?;
                } else {
                    print_line("negative result recorded");
                }
            }
            NegativeCommand::List => {
                let values = rlab_core::list_negative_results(&paths)?;
                if json {
                    print_json("journal_negative_list", values)?;
                } else {
                    for value in values {
                        print_line(&format!("{}: {}", value.hypothesis, value.reason));
                    }
                }
            }
            NegativeCommand::Search { term } => {
                let values = rlab_core::search_negative_results(&paths, &term)?;
                if json {
                    print_json("journal_negative_search", values)?;
                } else {
                    for value in values {
                        print_line(&format!("{}: {}", value.hypothesis, value.reason));
                    }
                }
            }
        },
        JournalSubcommand::Ideas { command } => match command {
            IdeasCommand::Add { text } => {
                let value = rlab_core::add_idea(&paths, &text)?;
                if json {
                    print_json("journal_ideas_add", value)?;
                } else {
                    print_line("idea recorded");
                }
            }
            IdeasCommand::List => {
                let values = rlab_core::list_ideas(&paths)?;
                if json {
                    print_json("journal_ideas_list", values)?;
                } else {
                    for value in values {
                        print_line(&format!("{} {:?}: {}", value.id, value.status, value.text));
                    }
                }
            }
            IdeasCommand::Promote { id, status } => {
                let status = rlab_core::IdeaStatus::parse(&status)?;
                let values = rlab_core::promote_idea(&paths, &id, status)?;
                if json {
                    print_json("journal_ideas_promote", values)?;
                } else {
                    print_line("idea status updated");
                }
            }
        },
    }
    Ok(0)
}
