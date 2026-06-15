use serde_json::Value;

use crate::error::{RlabError, RlabResult};
use crate::registry::RegistryRecord;

use super::{plan_experiment, ExperimentJob, ExperimentSpec, RetryPolicy};

const SCHEMA_VERSION: u32 = 1;
const KEY_HYPOTHESIS: &str = "hypothesis";
const KEY_MATRIX: &str = "matrix";
const KEY_METRICS: &str = "metrics";
const KEY_PARAMS: &str = "params";
const KEY_QUESTION: &str = "question";
const KEY_SEEDS: &str = "seeds";

pub fn plan_record_experiment(record: &RegistryRecord) -> RlabResult<Vec<ExperimentJob>> {
    let matrix = metadata_value(record, KEY_MATRIX, Value::Object(Default::default()));
    let seeds = metadata_value(record, KEY_SEEDS, Value::Array(Vec::new()));
    if is_empty_object(&matrix) && is_empty_array(&seeds) {
        return Ok(Vec::new());
    }

    let name = &record.name;
    let spec = ExperimentSpec {
        schema_version: SCHEMA_VERSION,
        name: name.clone(),
        question: optional_text(record, KEY_QUESTION),
        hypothesis: optional_text(record, KEY_HYPOTHESIS),
        params: decode_metadata(
            name,
            KEY_PARAMS,
            metadata_value(record, KEY_PARAMS, Value::Object(Default::default())),
        )?,
        matrix: decode_metadata(name, KEY_MATRIX, matrix)?,
        metrics: decode_metadata(
            name,
            KEY_METRICS,
            metadata_value(record, KEY_METRICS, Value::Array(Vec::new())),
        )?,
        seeds: decode_metadata(name, KEY_SEEDS, seeds)?,
        retry: RetryPolicy::none(),
    };
    Ok(plan_experiment(&spec)?.jobs)
}

fn metadata_value(record: &RegistryRecord, key: &str, default: Value) -> Value {
    match record.metadata.get(key) {
        Some(value) => value.clone(),
        None => default,
    }
}

fn optional_text(record: &RegistryRecord, key: &str) -> Option<String> {
    record
        .metadata
        .get(key)
        .and_then(Value::as_str)
        .map(str::to_owned)
}

fn decode_metadata<T: serde::de::DeserializeOwned>(
    experiment: &str,
    key: &str,
    value: Value,
) -> RlabResult<T> {
    serde_json::from_value(value).map_err(|error| {
        RlabError::validation(format!(
            "invalid experiment {key} for {experiment}: {error}"
        ))
    })
}

fn is_empty_object(value: &Value) -> bool {
    match value.as_object() {
        Some(object) => object.is_empty(),
        None => true,
    }
}

fn is_empty_array(value: &Value) -> bool {
    match value.as_array() {
        Some(array) => array.is_empty(),
        None => true,
    }
}
