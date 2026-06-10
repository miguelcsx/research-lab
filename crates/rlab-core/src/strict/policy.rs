use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StrictMode {
    Relaxed,
    Strict,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionPolicy {
    pub strict: bool,
    pub allow_lambdas: bool,
    pub allow_nested_functions: bool,
    pub allow_notebook_sources: bool,
    pub require_versions: bool,
}

impl ProductionPolicy {
    pub fn from_strict(strict: bool) -> Self {
        Self {
            strict,
            allow_lambdas: !strict,
            allow_nested_functions: !strict,
            allow_notebook_sources: !strict,
            require_versions: strict,
        }
    }
}
