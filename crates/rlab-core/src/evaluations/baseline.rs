use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::error::{RlabError, RlabResult};

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaselineEntry {
    pub schema_version: u32,
    pub name: String,
    pub metric: String,
    pub value: f64,
    pub description: Option<String>,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct BaselineStore {
    pub schema_version: u32,
    pub entries: BTreeMap<String, BaselineEntry>,
}

impl BaselineEntry {
    pub fn new(name: String, metric: String, value: f64, description: Option<String>) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            name,
            metric,
            value,
            description,
            created_at: OffsetDateTime::now_utc(),
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != SCHEMA_VERSION {
            return Err(RlabError::Validation {
                message: "unsupported baseline schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() || self.metric.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "baseline name and metric are required".to_string(),
            });
        }
        if !self.value.is_finite() {
            return Err(RlabError::Validation {
                message: "baseline value must be finite".to_string(),
            });
        }
        Ok(())
    }
}

impl BaselineStore {
    pub fn new() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            entries: BTreeMap::new(),
        }
    }

    pub fn insert(&mut self, entry: BaselineEntry) -> RlabResult<()> {
        entry.validate()?;
        self.entries.insert(entry.name.clone(), entry);
        Ok(())
    }
}
