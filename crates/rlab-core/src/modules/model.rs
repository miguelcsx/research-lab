use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleSummary {
    pub schema_version: u32,
    pub name: String,
    pub configured: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ModuleDiagnosticLevel {
    Info,
    Warning,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleDiagnostic {
    pub schema_version: u32,
    pub module: String,
    pub level: ModuleDiagnosticLevel,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleReloadPlan {
    pub schema_version: u32,
    pub modules: Vec<String>,
    pub purges_registry_cache: bool,
}
