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
        Self::validate_axes(&axes)?;

        Ok(Self {
            schema_version: SCHEMA_VERSION,
            axes,
        })
    }

    pub fn validate(&self) -> RlabResult<()> {
        validate_schema_version("grid", self.schema_version)?;
        Self::validate_axes(&self.axes)
    }

    pub fn validate_axes(axes: &BTreeMap<String, Vec<Value>>) -> RlabResult<()> {
        for (name, values) in axes {
            validate_axis_name("matrix", name)?;

            if values.is_empty() {
                return Err(RlabError::validation(format!(
                    "matrix axis {name} has no values"
                )));
            }
        }

        Ok(())
    }

    pub fn expand(&self) -> RlabResult<Vec<BTreeMap<String, Value>>> {
        self.validate()?;
        expand_axes(&self.axes)
    }

    pub fn expand_axes(
        axes: &BTreeMap<String, Vec<Value>>,
    ) -> RlabResult<Vec<BTreeMap<String, Value>>> {
        Self::validate_axes(axes)?;
        expand_axes(axes)
    }
}

impl Sample {
    pub fn validate(&self) -> RlabResult<()> {
        validate_schema_version("sample", self.schema_version)?;

        if self.n == 0 {
            return Err(RlabError::validation(
                "sample size must be greater than zero",
            ));
        }

        for (name, distribution) in &self.space {
            validate_axis_name("sample", name)?;
            distribution.validate()?;
        }

        Ok(())
    }
}

impl Distribution {
    pub fn validate(&self) -> RlabResult<()> {
        match self {
            Self::Choice { values } => validate_choice(values),
            Self::Uniform { low, high } => validate_bounds(*low, *high),
            Self::LogUniform { low, high } => {
                validate_bounds(*low, *high)?;

                if *low <= 0.0 {
                    return Err(RlabError::validation(
                        "log_uniform low bound must be positive",
                    ));
                }

                Ok(())
            }
        }
    }
}

fn expand_axes(axes: &BTreeMap<String, Vec<Value>>) -> RlabResult<Vec<BTreeMap<String, Value>>> {
    let capacity = grid_size(axes)?;
    let mut rows = Vec::with_capacity(capacity);
    rows.push(BTreeMap::new());

    for (axis, values) in axes {
        let next_capacity =
            checked_product(rows.len(), values.len(), "matrix expansion is too large")?;
        let mut next_rows = Vec::with_capacity(next_capacity);

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

fn validate_schema_version(kind: &str, schema_version: u32) -> RlabResult<()> {
    if schema_version == SCHEMA_VERSION {
        return Ok(());
    }

    Err(RlabError::validation(format!(
        "unsupported {kind} schema_version"
    )))
}

fn validate_axis_name(kind: &str, name: &str) -> RlabResult<()> {
    if !name.trim().is_empty() {
        return Ok(());
    }

    Err(RlabError::validation(format!(
        "{kind} axis name cannot be empty"
    )))
}

fn validate_choice(values: &[Value]) -> RlabResult<()> {
    if !values.is_empty() {
        return Ok(());
    }

    Err(RlabError::validation(
        "choice distribution requires at least one value",
    ))
}

fn validate_bounds(low: f64, high: f64) -> RlabResult<()> {
    if low.is_finite() && high.is_finite() && low < high {
        return Ok(());
    }

    Err(RlabError::validation(
        "distribution bounds must be finite and low < high",
    ))
}

fn grid_size(axes: &BTreeMap<String, Vec<Value>>) -> RlabResult<usize> {
    let mut size = 1usize;

    for values in axes.values() {
        size = checked_product(size, values.len(), "matrix expansion is too large")?;
    }

    Ok(size)
}

fn checked_product(left: usize, right: usize, message: &'static str) -> RlabResult<usize> {
    match left.checked_mul(right) {
        Some(value) => Ok(value),
        None => Err(RlabError::validation(message)),
    }
}
