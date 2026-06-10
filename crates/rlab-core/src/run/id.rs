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
        let timestamp: String = formatted.chars().filter(|ch| ch.is_ascii_alphanumeric()).collect();
        let safe_name: String = name
            .chars()
            .map(|ch| if matches!(ch, '/' | '\\' | ' ') { '_' } else { ch })
            .collect();
        Ok(Self(format!("{operation}_{safe_name}_{timestamp}")))
    }

    pub fn parse(value: String) -> RlabResult<Self> {
        if value.trim().is_empty() {
            return Err(RlabError::Run { message: "run id cannot be empty".to_string() });
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_contains_operation_and_name() {
        let id = RunId::new("experiment", "my_exp").unwrap();
        assert!(id.as_str().starts_with("experiment_my_exp_"));
    }

    #[test]
    fn new_sanitizes_path_separators() {
        let id = RunId::new("run", "a/b c").unwrap();
        assert!(!id.as_str().contains('/'));
        assert!(!id.as_str().contains(' '));
    }

    #[test]
    fn parse_empty_fails() {
        assert!(RunId::parse("".to_string()).is_err());
        assert!(RunId::parse("   ".to_string()).is_err());
    }

    #[test]
    fn parse_nonempty_succeeds() {
        let id = RunId::parse("experiment_foo_20240101".to_string()).unwrap();
        assert_eq!(id.as_str(), "experiment_foo_20240101");
    }
}
