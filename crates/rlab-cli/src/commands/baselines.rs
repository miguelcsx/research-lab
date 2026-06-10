use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct BaselinesCommand {
    #[command(subcommand)]
    pub command: BaselinesSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum BaselinesSubcommand {
    Add {
        name: String,
        #[arg(long)]
        metric: String,
        #[arg(long)]
        value: f64,
        #[arg(long)]
        description: Option<String>,
    },
    List,
    Compare {
        run_id: String,
    },
}

pub fn run(command: BaselinesCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        BaselinesSubcommand::Add {
            name,
            metric,
            value,
            description,
        } => {
            let baseline = rlab_core::add_baseline(&paths, &name, &metric, value, description)?;
            if json {
                print_json("baselines_add", baseline)?;
            } else {
                print_line("baseline added");
            }
        }
        BaselinesSubcommand::List => {
            let baselines = rlab_core::list_baselines(&paths)?;
            if json {
                print_json("baselines_list", baselines)?;
            } else {
                for baseline in baselines {
                    print_line(&format!(
                        "{} {}={}",
                        baseline.name, baseline.metric, baseline.value
                    ));
                }
            }
        }
        BaselinesSubcommand::Compare { run_id } => {
            let comparison = rlab_core::compare_baseline(&paths, &run_id)?;
            if json {
                print_json("baselines_compare", comparison)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&comparison)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
        }
    }
    Ok(0)
}
