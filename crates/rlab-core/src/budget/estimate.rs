use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetEstimate {
    pub schema_version: u32,
    pub jobs: u64,
    pub total_seconds: f64,
    pub total_storage_gb: f64,
}

pub fn estimate_budget(
    jobs: u64,
    seconds_per_job: f64,
    storage_gb_per_job: f64,
) -> RlabResult<BudgetEstimate> {
    if jobs == 0 {
        return Err(RlabError::Validation {
            message: "jobs must be greater than zero".to_string(),
        });
    }
    if !seconds_per_job.is_finite()
        || !storage_gb_per_job.is_finite()
        || seconds_per_job < 0.0
        || storage_gb_per_job < 0.0
    {
        return Err(RlabError::Validation {
            message: "budget inputs must be finite and non-negative".to_string(),
        });
    }
    Ok(BudgetEstimate {
        schema_version: SCHEMA_VERSION,
        jobs,
        total_seconds: seconds_per_job * jobs as f64,
        total_storage_gb: storage_gb_per_job * jobs as f64,
    })
}

pub fn estimate_required_repetitions(
    effect_size: f64,
    variance: f64,
    alpha: f64,
    power: f64,
) -> RlabResult<u64> {
    if !effect_size.is_finite() || !variance.is_finite() || !alpha.is_finite() || !power.is_finite()
    {
        return Err(RlabError::Validation {
            message: "power inputs must be finite".to_string(),
        });
    }
    if effect_size <= 0.0
        || variance < 0.0
        || !(0.0..1.0).contains(&alpha)
        || !(0.0..1.0).contains(&power)
    {
        return Err(RlabError::Validation {
            message: "invalid power-analysis inputs".to_string(),
        });
    }
    let z_alpha = 1.96_f64;
    let z_power = if power >= 0.9 {
        1.28
    } else if power >= 0.8 {
        0.84
    } else {
        0.52
    };
    let n = 2.0 * variance * (z_alpha + z_power).powi(2) / effect_size.powi(2);
    Ok(n.ceil().max(1.0) as u64)
}
