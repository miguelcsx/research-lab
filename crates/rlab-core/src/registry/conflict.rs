use std::collections::BTreeSet;

use crate::error::{RlabError, RlabResult};

use super::record::Registry;

pub fn validate_no_conflicts(registry: &Registry) -> RlabResult<()> {
    let mut seen = BTreeSet::new();

    for record in &registry.records {
        let key = (record.kind.as_str(), record.name.as_str());

        if !seen.insert(key) {
            return Err(RlabError::registry(format!(
                "duplicate registry key: {}:{}",
                key.0, key.1
            )));
        }
    }

    Ok(())
}
