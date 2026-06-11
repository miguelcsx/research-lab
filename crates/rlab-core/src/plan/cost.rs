use serde::{Deserialize, Serialize};

use crate::budget::estimate_budget;
use crate::error::RlabResult;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostPlan {
    pub schema_version: u32,
    pub jobs: u64,
    pub seconds: f64,
    pub storage_gb: f64,
}

pub fn estimate_cost(
    jobs: u64,
    seconds_per_job: f64,
    storage_gb_per_job: f64,
) -> RlabResult<CostPlan> {
    let estimate = estimate_budget(jobs, seconds_per_job, storage_gb_per_job)?;
    Ok(CostPlan {
        schema_version: SCHEMA_VERSION,
        jobs,
        seconds: estimate.total_seconds,
        storage_gb: estimate.total_storage_gb,
    })
}
