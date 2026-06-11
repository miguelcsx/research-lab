use crate::error::{RlabError, RlabResult};

const EMPTY_VALUE_MESSAGE_SUFFIX: &str = "cannot be empty";

pub fn validate_non_empty(label: &str, value: &str) -> RlabResult<()> {
    if !value.trim().is_empty() {
        return Ok(());
    }

    Err(RlabError::Config {
        message: format!("{label} {EMPTY_VALUE_MESSAGE_SUFFIX}"),
    })
}

