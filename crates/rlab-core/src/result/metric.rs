use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::error::{RlabError, RlabResult};

pub const METRIC_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricDirection {
    Minimize,
    Maximize,
    Neutral,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metric {
    pub schema_version: u32,
    pub name: String,
    pub value: f64,
    pub unit: Option<String>,
    pub direction: Option<MetricDirection>,
    #[serde(with = "time::serde::rfc3339")]
    pub timestamp: OffsetDateTime,
}

impl Metric {
    pub fn new(
        name: String,
        value: f64,
        unit: Option<String>,
        direction: Option<MetricDirection>,
    ) -> Self {
        Self {
            schema_version: METRIC_SCHEMA_VERSION,
            name,
            value,
            unit,
            direction,
            timestamp: OffsetDateTime::now_utc(),
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != METRIC_SCHEMA_VERSION {
            return Err(RlabError::Validation {
                message: "unsupported metric schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "metric name cannot be empty".to_string(),
            });
        }
        if !self.value.is_finite() {
            return Err(RlabError::Validation {
                message: format!("metric {} value must be finite", self.name),
            });
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_metric_passes() {
        let m = Metric::new(
            "loss".to_string(),
            0.42,
            None,
            Some(MetricDirection::Minimize),
        );
        assert!(m.validate().is_ok());
    }

    #[test]
    fn empty_name_fails() {
        let m = Metric::new("  ".to_string(), 1.0, None, None);
        assert!(m.validate().is_err());
    }

    #[test]
    fn nan_value_fails() {
        let m = Metric::new("loss".to_string(), f64::NAN, None, None);
        assert!(m.validate().is_err());
    }

    #[test]
    fn infinite_value_fails() {
        let m = Metric::new("loss".to_string(), f64::INFINITY, None, None);
        assert!(m.validate().is_err());
    }

    #[test]
    fn direction_serde_roundtrip() {
        let json = serde_json::to_string(&MetricDirection::Minimize).unwrap();
        assert_eq!(json, r#""minimize""#);
        let back: MetricDirection = serde_json::from_str(&json).unwrap();
        assert_eq!(back, MetricDirection::Minimize);
    }
}
