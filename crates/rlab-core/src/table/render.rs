use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableRender {
    pub schema_version: u32,
    pub path: String,
    pub text: String,
}

pub fn render_table(path: &Path) -> RlabResult<TableRender> {
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    Ok(TableRender { schema_version: SCHEMA_VERSION, path: path.display().to_string(), text })
}
