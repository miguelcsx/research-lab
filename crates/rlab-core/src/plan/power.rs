use serde::{Deserialize, Serialize};

use crate::budget::estimate_required_repetitions;
use crate::error::RlabResult;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerPlan {
    pub schema_version: u32,
    pub repetitions: u64,
}

pub fn estimate_power_repetitions(effect_size: f64, variance: f64, alpha: f64, power: f64) -> RlabResult<PowerPlan> {
    Ok(PowerPlan { schema_version: SCHEMA_VERSION, repetitions: estimate_required_repetitions(effect_size, variance, alpha, power)? })
}
