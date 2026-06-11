use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

const SECRET_KEYWORDS: [&str; 5] = ["token", "secret", "password", "credential", "key"];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretHit {
    pub key: String,
    pub reason: String,
}

pub fn redact_secrets(env: &BTreeMap<String, String>) -> BTreeMap<String, String> {
    env.iter()
        .map(|(key, value)| {
            if is_sensitive_key(key) {
                (key.clone(), "<redacted>".to_string())
            } else {
                (key.clone(), value.clone())
            }
        })
        .collect()
}

pub fn scan_for_secrets(text: &str) -> Vec<SecretHit> {
    text.lines()
        .filter_map(|line| line.split_once('='))
        .filter_map(|(key, _value)| {
            if is_sensitive_key(key) {
                Some(SecretHit {
                    key: key.to_string(),
                    reason: "sensitive key name".to_string(),
                })
            } else {
                None
            }
        })
        .collect()
}

fn is_sensitive_key(key: &str) -> bool {
    let lowered = key.to_lowercase();
    SECRET_KEYWORDS
        .iter()
        .any(|needle| lowered.contains(needle))
}
