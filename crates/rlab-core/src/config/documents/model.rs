use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ResolvedDocument {
    pub name: String,
    pub source: PathBuf,
    pub value: Value,
    pub overrides: BTreeMap<String, Value>,
}
