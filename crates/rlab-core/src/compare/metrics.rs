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
    pub effect_size: Option<f64>,
    pub confidence_interval: Option<(f64, f64)>,
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
        effect_size: standardized_effect(a, b)?,
        confidence_interval: None,
    })
}

pub fn paired_bootstrap(
    a: &[f64],
    b: &[f64],
    samples: usize,
    confidence: f64,
    seed: u64,
) -> RlabResult<MetricComparison> {
    if a.len() != b.len() || a.is_empty() {
        return Err(RlabError::Validation {
            message: "paired arrays must be non-empty and equal length".to_string(),
        });
    }
    if samples == 0 || !(0.0..1.0).contains(&confidence) {
        return Err(RlabError::Validation {
            message: "invalid bootstrap configuration".to_string(),
        });
    }
    validate_finite(a)?;
    validate_finite(b)?;

    let differences = a
        .iter()
        .zip(b)
        .map(|(left, right)| right - left)
        .collect::<Vec<_>>();
    let mut rng = DeterministicRng::new(seed);
    let mut estimates = Vec::with_capacity(samples);
    for _ in 0..samples {
        let mut total = 0.0;
        for _ in &differences {
            total += differences[rng.index(differences.len())];
        }
        estimates.push(total / differences.len() as f64);
    }
    estimates.sort_by(|left, right| left.total_cmp(right));

    let tail = (1.0 - confidence) / 2.0;
    let lower = estimates[((tail * samples as f64) as usize).min(samples - 1)];
    let upper = estimates[(((1.0 - tail) * samples as f64) as usize).min(samples - 1)];
    let mut comparison = compare_metric_arrays(a, b)?;
    comparison.confidence_interval = Some((lower, upper));
    Ok(comparison)
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

fn validate_finite(values: &[f64]) -> RlabResult<()> {
    mean(values).map(|_| ())
}

fn standardized_effect(a: &[f64], b: &[f64]) -> RlabResult<Option<f64>> {
    let differences = a
        .iter()
        .zip(b)
        .map(|(left, right)| {
            if !left.is_finite() || !right.is_finite() {
                return Err(RlabError::Validation {
                    message: "metric array contains non-finite value".to_string(),
                });
            }
            Ok(right - left)
        })
        .collect::<RlabResult<Vec<_>>>()?;
    if differences.len() < 2 {
        return Ok(None);
    }
    let center = differences.iter().sum::<f64>() / differences.len() as f64;
    let variance = differences
        .iter()
        .map(|value| (value - center).powi(2))
        .sum::<f64>()
        / (differences.len() - 1) as f64;
    let deviation = variance.sqrt();
    Ok((deviation != 0.0).then_some(center / deviation))
}

struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    fn index(&mut self, len: usize) -> usize {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.state % len as u64) as usize
    }
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

    #[test]
    fn bootstrap_is_deterministic() {
        let first = paired_bootstrap(&[1.0, 2.0, 4.0], &[2.0, 2.5, 5.5], 200, 0.95, 0).unwrap();
        let second = paired_bootstrap(&[1.0, 2.0, 4.0], &[2.0, 2.5, 5.5], 200, 0.95, 0).unwrap();
        assert_eq!(first.confidence_interval, second.confidence_interval);
    }
}
