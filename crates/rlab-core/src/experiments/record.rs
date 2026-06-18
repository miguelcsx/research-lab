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
    let params = metadata_value(record, KEY_PARAMS, Value::Object(Default::default()));
    let seeds = metadata_value(record, KEY_SEEDS, Value::Array(Vec::new()));
    if is_empty_object(&matrix) && is_empty_object(&params) && is_empty_array(&seeds) {
        return Ok(Vec::new());
    }

    let name = &record.name;
    let spec = ExperimentSpec {
        schema_version: SCHEMA_VERSION,
        name: name.clone(),
        question: optional_text(record, KEY_QUESTION),
        hypothesis: optional_text(record, KEY_HYPOTHESIS),
        params: decode_metadata(name, KEY_PARAMS, params)?,
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

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::path::PathBuf;

    use serde_json::json;

    use crate::registry::{RegistryKind, RegistryRecord};

    use super::plan_record_experiment;

    #[test]
    fn params_only_experiment_plans_one_job() {
        let record = RegistryRecord {
            schema_version: 1,
            kind: RegistryKind::EXPERIMENT,
            name: "configured".to_string(),
            version: "1".to_string(),
            module: "tests".to_string(),
            qualname: "configured".to_string(),
            source: PathBuf::from("tests.py"),
            tags: Vec::new(),
            description: String::new(),
            metadata: BTreeMap::from([(
                "params".to_string(),
                json!({"runtime.max_words_seen": 20}),
            )]),
        };

        let jobs = plan_record_experiment(&record).expect("valid experiment plan");

        assert_eq!(jobs.len(), 1);
        assert_eq!(
            jobs[0].params.get("runtime.max_words_seen"),
            Some(&json!(20))
        );
    }
}
