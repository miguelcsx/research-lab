use std::path::Path;

use crate::error::{RlabError, RlabResult};
use crate::fs::append_line;

use super::manifest::ArtifactManifest;

pub fn append_index_row(index_path: &Path, manifest: &ArtifactManifest) -> RlabResult<()> {
    let line = serde_json::to_string(manifest).map_err(RlabError::serialization)?;
    append_line(index_path, &line)
}
