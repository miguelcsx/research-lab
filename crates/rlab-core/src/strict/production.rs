use crate::error::{RlabError, RlabResult};
use crate::registry::RegistryRecord;

use super::policy::ProductionPolicy;

pub fn validate_record_for_production(
    record: &RegistryRecord,
    policy: &ProductionPolicy,
) -> RlabResult<()> {
    if !policy.strict {
        return Ok(());
    }
    if policy.require_versions && record.version.trim().is_empty() {
        return Err(RlabError::Validation {
            message: format!("{}:{} has no version", record.kind.as_str(), record.name),
        });
    }
    let source_text = record.source.display().to_string();
    if source_text.trim().is_empty() || source_text.starts_with('<') {
        return Err(RlabError::Validation {
            message: format!(
                "{}:{} has no stable source file",
                record.kind.as_str(),
                record.name
            ),
        });
    }
    if !policy.allow_lambdas && record.qualname.contains("<lambda>") {
        return Err(RlabError::Validation {
            message: format!(
                "{}:{} is a lambda and cannot be used in strict mode",
                record.kind.as_str(),
                record.name
            ),
        });
    }
    if !policy.allow_nested_functions && record.qualname.contains("<locals>") {
        return Err(RlabError::Validation {
            message: format!(
                "{}:{} is nested and cannot be used in strict mode",
                record.kind.as_str(),
                record.name
            ),
        });
    }
    if !policy.allow_notebook_sources && source_text.ends_with(".ipynb") {
        return Err(RlabError::Validation {
            message: format!(
                "{}:{} is notebook-only and cannot be used in strict mode",
                record.kind.as_str(),
                record.name
            ),
        });
    }
    Ok(())
}
