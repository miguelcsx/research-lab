use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct PromoteRequest {
    pub source: PathBuf,
    pub artifact_kind: String,
    pub name: String,
    pub version: String,
    pub alias: Option<String>,
}
