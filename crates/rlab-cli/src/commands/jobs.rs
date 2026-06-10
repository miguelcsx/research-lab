use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct JobsCommand {
    #[command(subcommand)]
    pub command: JobsSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum JobsSubcommand {
    Start { command: String },
    List,
    Logs { id: String },
    Cancel { id: String },
}

pub fn run(command: JobsCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        JobsSubcommand::Start { command } => {
            let job = rlab_core::start_job(&paths, &command)?;
            if json {
                print_json("jobs_start", job)?;
            } else {
                print_line(&format!("job {} completed", job.id));
            }
        }
        JobsSubcommand::List => {
            let jobs = rlab_core::list_jobs(&paths)?;
            if json {
                print_json("jobs_list", jobs)?;
            } else {
                for job in jobs {
                    print_line(&format!("{} {:?} {}", job.id, job.status, job.command));
                }
            }
        }
        JobsSubcommand::Logs { id } => {
            let logs = rlab_core::job_logs(&paths, &id)?;
            if json {
                print_json("jobs_logs", logs)?;
            } else {
                print_line(&logs);
            }
        }
        JobsSubcommand::Cancel { id } => {
            let job = rlab_core::cancel_job(&paths, &id)?;
            if json {
                print_json("jobs_cancel", job)?;
            } else {
                print_line("job cancelled");
            }
        }
    }
    Ok(0)
}
