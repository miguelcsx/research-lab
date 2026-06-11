use serde::{Deserialize, Serialize};

use crate::error::RlabResult;

use super::descriptive::{describe_array, DescriptiveStats};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SampleComparison {
    pub schema_version: u32,
    pub left: DescriptiveStats,
    pub right: DescriptiveStats,
    pub mean_delta: f64,
    pub relative_delta: Option<f64>,
}

pub fn compare_samples(left: &[f64], right: &[f64]) -> RlabResult<SampleComparison> {
    let left_stats = describe_array(left)?;
    let right_stats = describe_array(right)?;
    let mean_delta = right_stats.mean - left_stats.mean;
    let relative_delta = if left_stats.mean == 0.0 {
        None
    } else {
        Some(mean_delta / left_stats.mean)
    };
    Ok(SampleComparison {
        schema_version: SCHEMA_VERSION,
        left: left_stats,
        right: right_stats,
        mean_delta,
        relative_delta,
    })
}
