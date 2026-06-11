use crate::error::RlabResult;

use super::strings::validate_non_empty;

const PROJECT_NAME_LABEL: &str = "project name";

pub fn validate_project_name(name: &str) -> RlabResult<()> {
    validate_non_empty(PROJECT_NAME_LABEL, name)
}
