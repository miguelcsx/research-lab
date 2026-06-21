pub mod adapters;
pub mod artifact;
pub mod baselines;
pub mod benchmark;
pub mod cache;
pub mod ci;
pub mod clean;
pub mod compare;
pub mod config;
pub mod discover;
pub mod doctor;
pub mod errors;
pub mod evaluate;
pub mod exec;
pub mod explain;
pub mod freeze;
pub mod graph;
pub mod handoff;
pub mod impact;
pub mod init;
pub mod invalidate;
pub mod jobs;
pub mod journal;
pub mod lint;
pub mod migrate;
pub mod modules;
pub mod notes;
pub mod plan;
pub mod report;
pub mod run;
pub mod runs;
pub mod search;
pub mod stats;
pub mod study;
pub mod table;
pub mod validate;

use rlab_core::{RegistryKind, RegistryRecord};

pub(crate) fn records_targeting<'a>(
    records: &'a [RegistryRecord],
    kind: RegistryKind,
    target: &str,
) -> Vec<&'a RegistryRecord> {
    records
        .iter()
        .filter(|record| record.kind == kind)
        .filter(|record| {
            record
                .metadata
                .get("target")
                .and_then(serde_json::Value::as_str)
                .is_some_and(|pattern| target_matches(pattern, target))
        })
        .collect()
}

fn target_matches(pattern: &str, target: &str) -> bool {
    pattern == target
        || pattern.strip_suffix(":*").is_some_and(|kind| {
            target
                .strip_prefix(kind)
                .is_some_and(|rest| rest.starts_with(':'))
        })
}

#[cfg(test)]
mod tests {
    use super::target_matches;

    #[test]
    fn matches_exact_or_kind_wildcard_targets() {
        assert!(target_matches("model:babylm", "model:babylm"));
        assert!(target_matches("attention:*", "attention:manual"));
        assert!(!target_matches("attention:*", "tokenizer:bbpe"));
    }
}
