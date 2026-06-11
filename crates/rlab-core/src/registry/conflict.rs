use std::collections::BTreeSet;

use crate::error::{RlabError, RlabResult};

use super::record::Registry;

pub fn validate_no_conflicts(registry: &Registry) -> RlabResult<()> {
    let mut seen = BTreeSet::new();
    for record in &registry.records {
        let key = (record.kind.as_str().to_string(), record.name.clone());
        if !seen.insert(key.clone()) {
            return Err(RlabError::Registry {
                message: format!("duplicate registry key: {}:{}", key.0, key.1),
            });
        }
    }
    Ok(())
}
