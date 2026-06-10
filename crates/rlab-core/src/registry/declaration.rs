use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeclarationMetadata {
    pub module: String,
    pub qualname: String,
    pub source: String,
    pub description: String,
}
