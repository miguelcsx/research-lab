use crate::config::EffectiveConfig;

use super::model::{ModuleDiagnostic, ModuleDiagnosticLevel, ModuleReloadPlan, ModuleSummary};
const SCHEMA_VERSION: u32 = 1;

pub fn list_modules(config: &EffectiveConfig) -> Vec<ModuleSummary> {
    config.python.modules.iter().map(|name| ModuleSummary { schema_version: SCHEMA_VERSION, name: name.clone(), configured: true }).collect()
}

pub fn diagnose_modules(config: &EffectiveConfig) -> Vec<ModuleDiagnostic> {
    if config.python.modules.is_empty() {
        return vec![ModuleDiagnostic {
            schema_version: SCHEMA_VERSION,
            module: "<inferred>".to_string(),
            level: ModuleDiagnosticLevel::Warning,
            message: "no Python modules configured; discovery will rely on zero-config inference".to_string(),
        }];
    }
    config.python.modules.iter().map(|module| ModuleDiagnostic {
        schema_version: SCHEMA_VERSION,
        module: module.clone(),
        level: ModuleDiagnosticLevel::Info,
        message: "module is configured for Python runner discovery".to_string(),
    }).collect()
}

pub fn reload_modules_plan(config: &EffectiveConfig) -> ModuleReloadPlan {
    ModuleReloadPlan { schema_version: SCHEMA_VERSION, modules: config.python.modules.clone(), purges_registry_cache: true }
}
