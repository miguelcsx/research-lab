use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
use crate::fs::{append_line, ensure_dir, write_json_atomic};

use super::model::DataDecision;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaterializeReport {
    pub schema_version: u32,
    pub written_records: usize,
    pub dropped_records: usize,
    pub drop_reasons: BTreeMap<String, usize>,
}

pub fn materialize_records<I>(output_dir: &Path, decisions: I) -> RlabResult<MaterializeReport>
where
    I: IntoIterator<Item = DataDecision>,
{
    ensure_dir(output_dir)?;
    let data_path = output_dir.join("data.jsonl");
    let mut report = MaterializeReport {
        schema_version: SCHEMA_VERSION,
        written_records: 0,
        dropped_records: 0,
        drop_reasons: BTreeMap::new(),
    };
    for decision in decisions {
        match decision {
            DataDecision::Keep { record, .. } | DataDecision::Update { record, .. } => {
                validate_json_object(&record)?;
                append_line(
                    &data_path,
                    &serde_json::to_string(&record).map_err(RlabError::serialization)?,
                )?;
                report.written_records += 1;
            }
            DataDecision::Drop { reason, .. } => {
                report.dropped_records += 1;
                let count = report.drop_reasons.entry(reason).or_insert(0);
                *count += 1;
            }
            DataDecision::Boundary { .. } => {
                return Err(RlabError::Validation {
                    message: "data boundary reached sink without being consumed".to_string(),
                });
            }
        }
    }
    write_json_atomic(&output_dir.join("manifest.json"), &report)?;
    Ok(report)
}

fn validate_json_object(value: &Value) -> RlabResult<()> {
    if value.is_object() {
        Ok(())
    } else {
        Err(RlabError::Validation {
            message: "materialized data records must be JSON objects".to_string(),
        })
    }
}
