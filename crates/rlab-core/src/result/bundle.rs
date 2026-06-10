use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use super::metric::Metric;

pub const RESULT_BUNDLE_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResultBundle {
    pub schema_version: u32,
    pub metrics: Vec<Metric>,
    pub data: BTreeMap<String, Value>,
}

impl ResultBundle {
    pub fn empty() -> Self {
        Self { schema_version: RESULT_BUNDLE_SCHEMA_VERSION, metrics: Vec::new(), data: BTreeMap::new() }
    }

    pub fn from_metric_map(metrics: BTreeMap<String, f64>) -> Self {
        let metric_values = metrics
            .into_iter()
            .map(|(name, value)| Metric::new(name, value, None, None))
            .collect();
        Self { schema_version: RESULT_BUNDLE_SCHEMA_VERSION, metrics: metric_values, data: BTreeMap::new() }
    }
}
