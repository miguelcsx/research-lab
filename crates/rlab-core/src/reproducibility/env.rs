use serde_json::{json, Value};

use crate::error::redact_secrets;
const SCHEMA_VERSION: u32 = 1;

pub fn capture_environment() -> Value {
    let variables: Vec<Value> = std::env::vars()
        .map(|(key, value)| json!({"key": key, "value": redact_secrets(&value)}))
        .collect();
    json!({
        "schema_version": SCHEMA_VERSION,
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "vars": variables,
    })
}
