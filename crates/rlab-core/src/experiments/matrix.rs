use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MatrixValue {
    Values(Vec<Value>),
    Distribution(Distribution),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Distribution {
    Choice { values: Vec<Value> },
    Uniform { low: f64, high: f64 },
    LogUniform { low: f64, high: f64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Choice {
    pub values: Vec<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Grid {
    pub schema_version: u32,
    pub axes: BTreeMap<String, Vec<Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sample {
    pub schema_version: u32,
    pub space: BTreeMap<String, Distribution>,
    pub n: usize,
    pub seed: u64,
}

impl Grid {
    pub fn new(axes: BTreeMap<String, Vec<Value>>) -> RlabResult<Self> {
        let grid = Self { schema_version: SCHEMA_VERSION, axes };
        grid.validate()?;
        Ok(grid)
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation { message: "unsupported grid schema_version".to_string() });
        }
        for (name, values) in &self.axes {
            if name.trim().is_empty() {
                return Err(RlabError::Validation { message: "matrix axis name cannot be empty".to_string() });
            }
            if values.is_empty() {
                return Err(RlabError::Validation { message: format!("matrix axis {name} has no values") });
            }
        }
        Ok(())
    }

    pub fn expand(&self) -> RlabResult<Vec<BTreeMap<String, Value>>> {
        self.validate()?;
        let mut rows = vec![BTreeMap::new()];
        for (axis, values) in &self.axes {
            let mut next_rows = Vec::new();
            for row in &rows {
                for value in values {
                    let mut next = row.clone();
                    next.insert(axis.clone(), value.clone());
                    next_rows.push(next);
                }
            }
            rows = next_rows;
        }
        Ok(rows)
    }
}

impl Sample {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation { message: "unsupported sample schema_version".to_string() });
        }
        if self.n == 0 {
            return Err(RlabError::Validation { message: "sample size must be greater than zero".to_string() });
        }
        for (name, distribution) in &self.space {
            if name.trim().is_empty() {
                return Err(RlabError::Validation { message: "sample axis name cannot be empty".to_string() });
            }
            distribution.validate()?;
        }
        Ok(())
    }
}

impl Distribution {
    pub fn validate(&self) -> RlabResult<()> {
        match self {
            Self::Choice { values } if values.is_empty() => Err(RlabError::Validation { message: "choice distribution requires at least one value".to_string() }),
            Self::Uniform { low, high } | Self::LogUniform { low, high } => {
                if !low.is_finite() || !high.is_finite() || low >= high {
                    return Err(RlabError::Validation { message: "distribution bounds must be finite and low < high".to_string() });
                }
                if matches!(self, Self::LogUniform { .. }) && *low <= 0.0 {
                    return Err(RlabError::Validation { message: "log_uniform low bound must be positive".to_string() });
                }
                Ok(())
            }
            _ => Ok(()),
        }
    }
}
