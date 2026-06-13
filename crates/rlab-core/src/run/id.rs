use serde::{Deserialize, Serialize};
use time::{format_description::well_known::Rfc3339, OffsetDateTime};

use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct RunId(String);

impl RunId {
    pub fn new(operation: &str, name: &str) -> RlabResult<Self> {
        let formatted = OffsetDateTime::now_utc()
            .format(&Rfc3339)
            .map_err(RlabError::serialization)?;
        let timestamp = compact_timestamp(&formatted);
        let safe_name = safe_id_component(name);

        Ok(Self(format!("{operation}_{safe_name}_{timestamp}")))
    }

    pub fn parse(value: String) -> RlabResult<Self> {
        if !value.trim().is_empty() {
            return Ok(Self(value));
        }

        Err(RlabError::Run {
            message: "run id cannot be empty".to_string(),
        })
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn compact_timestamp(value: &str) -> String {
    value.chars().filter(char::is_ascii_alphanumeric).collect()
}

fn safe_id_component(value: &str) -> String {
    value.chars().map(safe_id_character).collect()
}

fn safe_id_character(character: char) -> char {
    if character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-') {
        return character;
    }

    '_'
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_contains_operation_and_name() {
        let id = expect_ok(RunId::new("experiment", "my_exp"));

        assert!(id.as_str().starts_with("experiment_my_exp_"));
    }

    #[test]
    fn new_sanitizes_path_separators() {
        let id = expect_ok(RunId::new("run", "a/b c"));

        assert!(!id.as_str().contains('/'));
        assert!(!id.as_str().contains(' '));
    }

    #[test]
    fn parse_empty_fails() {
        assert!(RunId::parse(String::new()).is_err());
        assert!(RunId::parse("   ".to_string()).is_err());
    }

    #[test]
    fn parse_nonempty_succeeds() {
        let id = expect_ok(RunId::parse("experiment_foo_20240101".to_string()));

        assert_eq!(id.as_str(), "experiment_foo_20240101");
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }
}
