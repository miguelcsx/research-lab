use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DescriptiveStats {
    pub schema_version: u32,
    pub count: usize,
    pub mean: f64,
    pub min: f64,
    pub max: f64,
    pub variance: f64,
}

pub fn describe_array(values: &[f64]) -> RlabResult<DescriptiveStats> {
    if values.is_empty() {
        return Err(RlabError::Validation { message: "cannot describe an empty array".to_string() });
    }
    let count = values.len();
    let sum = values.iter().copied().sum::<f64>();
    let mean = sum / count as f64;
    let mut min = values[0];
    let mut max = values[0];
    for value in values.iter().copied().skip(1) {
        if value < min { min = value; }
        if value > max { max = value; }
    }
    let variance = values.iter().map(|value| { let delta = value - mean; delta * delta }).sum::<f64>() / count as f64;
    Ok(DescriptiveStats { schema_version: SCHEMA_VERSION, count, mean, min, max, variance })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_fails() {
        assert!(describe_array(&[]).is_err());
    }

    #[test]
    fn single_value() {
        let stats = describe_array(&[5.0]).unwrap();
        assert_eq!(stats.count, 1);
        assert!((stats.mean - 5.0).abs() < 1e-10);
        assert!((stats.min - 5.0).abs() < 1e-10);
        assert!((stats.max - 5.0).abs() < 1e-10);
        assert!((stats.variance).abs() < 1e-10);
    }

    #[test]
    fn known_array() {
        let stats = describe_array(&[1.0, 2.0, 3.0, 4.0, 5.0]).unwrap();
        assert_eq!(stats.count, 5);
        assert!((stats.mean - 3.0).abs() < 1e-10);
        assert!((stats.min - 1.0).abs() < 1e-10);
        assert!((stats.max - 5.0).abs() < 1e-10);
        assert!((stats.variance - 2.0).abs() < 1e-10);
    }
}
