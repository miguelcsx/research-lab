use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricComparison {
    pub schema_version: u32,
    pub mean_a: f64,
    pub mean_b: f64,
    pub delta: f64,
    pub count_a: usize,
    pub count_b: usize,
}

pub fn compare_metric_arrays(a: &[f64], b: &[f64]) -> RlabResult<MetricComparison> {
    if a.is_empty() || b.is_empty() {
        return Err(RlabError::Validation {
            message: "metric arrays must not be empty".to_string(),
        });
    }
    let mean_a = mean(a)?;
    let mean_b = mean(b)?;
    Ok(MetricComparison {
        schema_version: SCHEMA_VERSION,
        mean_a,
        mean_b,
        delta: mean_b - mean_a,
        count_a: a.len(),
        count_b: b.len(),
    })
}

fn mean(values: &[f64]) -> RlabResult<f64> {
    let mut total = 0.0_f64;
    for value in values {
        if !value.is_finite() {
            return Err(RlabError::Validation {
                message: "metric array contains non-finite value".to_string(),
            });
        }
        total += value;
    }
    Ok(total / values.len() as f64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_input_fails() {
        assert!(compare_metric_arrays(&[], &[1.0]).is_err());
        assert!(compare_metric_arrays(&[1.0], &[]).is_err());
    }

    #[test]
    fn correct_delta() {
        let result = compare_metric_arrays(&[1.0, 2.0], &[3.0, 4.0]).unwrap();
        assert!((result.mean_a - 1.5).abs() < 1e-10);
        assert!((result.mean_b - 3.5).abs() < 1e-10);
        assert!((result.delta - 2.0).abs() < 1e-10);
    }

    #[test]
    fn counts_are_correct() {
        let result = compare_metric_arrays(&[1.0, 2.0, 3.0], &[4.0]).unwrap();
        assert_eq!(result.count_a, 3);
        assert_eq!(result.count_b, 1);
    }

    #[test]
    fn non_finite_value_fails() {
        assert!(compare_metric_arrays(&[f64::NAN], &[1.0]).is_err());
        assert!(compare_metric_arrays(&[1.0], &[f64::INFINITY]).is_err());
    }
}
