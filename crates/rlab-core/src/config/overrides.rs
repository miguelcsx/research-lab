use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigOverride {
    pub path: Vec<String>,
    pub value: Value,
}
