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
        validate_schema_version(self.schema_version)?;
        validate_name(&self.name)?;
        validate_value(&self.name, self.value)
    }
}

fn validate_schema_version(schema_version: u32) -> RlabResult<()> {
    if schema_version == METRIC_SCHEMA_VERSION {
        return Ok(());
    }

    validation_error("unsupported metric schema_version")
}

fn validate_name(name: &str) -> RlabResult<()> {
    if !name.trim().is_empty() {
        return Ok(());
    }

    validation_error("metric name cannot be empty")
}

fn validate_value(name: &str, value: f64) -> RlabResult<()> {
    if value.is_finite() {
        return Ok(());
    }

    validation_error(format!("metric {name} value must be finite"))
}

fn validation_error<T>(message: impl Into<String>) -> RlabResult<T> {
    Err(RlabError::Validation {
        message: message.into(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_metric_passes() {
        let metric = Metric::new(
            "loss".to_string(),
            0.42,
            None,
            Some(MetricDirection::Minimize),
        );

        assert!(metric.validate().is_ok());
    }

    #[test]
    fn empty_name_fails() {
        let metric = Metric::new("  ".to_string(), 1.0, None, None);

        assert!(metric.validate().is_err());
    }

    #[test]
    fn nan_value_fails() {
        let metric = Metric::new("loss".to_string(), f64::NAN, None, None);

        assert!(metric.validate().is_err());
    }

    #[test]
    fn infinite_value_fails() {
        let metric = Metric::new("loss".to_string(), f64::INFINITY, None, None);

        assert!(metric.validate().is_err());
    }

    #[test]
    fn direction_serde_roundtrip() {
        let json = expect_ok(serde_json::to_string(&MetricDirection::Minimize));

        assert_eq!(json, r#""minimize""#);

        let back: MetricDirection = expect_ok(serde_json::from_str(&json));

        assert_eq!(back, MetricDirection::Minimize);
    }

    fn expect_ok<T, E: std::fmt::Display>(result: Result<T, E>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }
}
