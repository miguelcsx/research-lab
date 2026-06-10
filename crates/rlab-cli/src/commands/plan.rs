use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct PlanCommand {
    #[command(subcommand)]
    pub command: PlanSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum PlanSubcommand {
    Power {
        #[arg(long)]
        effect_size: f64,
        #[arg(long)]
        variance: f64,
        #[arg(long)]
        alpha: f64,
        #[arg(long)]
        power: f64,
    },
    Cost {
        #[arg(long)]
        jobs: u64,
        #[arg(long)]
        seconds_per_job: f64,
        #[arg(long)]
        storage_gb_per_job: f64,
    },
}

pub fn run(command: PlanCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let _config = load_effective_config(root, &[])?;
    match command.command {
        PlanSubcommand::Power {
            effect_size,
            variance,
            alpha,
            power,
        } => {
            let result =
                rlab_core::estimate_power_repetitions(effect_size, variance, alpha, power)?;
            if json {
                print_json("plan_power", result)?;
            } else {
                print_line(&format!("required repetitions: {}", result.repetitions));
            }
        }
        PlanSubcommand::Cost {
            jobs,
            seconds_per_job,
            storage_gb_per_job,
        } => {
            let result = rlab_core::estimate_cost(jobs, seconds_per_job, storage_gb_per_job)?;
            if json {
                print_json("plan_cost", result)?;
            } else {
                print_line(&format!(
                    "seconds={} storage_gb={}",
                    result.seconds, result.storage_gb
                ));
            }
        }
    }
    Ok(0)
}
