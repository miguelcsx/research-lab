use std::fs;
use std::path::Path;

use crate::error::{RlabError, RlabResult};

pub fn init_project(root: &Path, name: &str) -> RlabResult<()> {
    fs::create_dir_all(root.join("experiments"))
        .map_err(|error| RlabError::io(root.join("experiments"), error))?;
    fs::write(root.join("experiments/__init__.py"), "")
        .map_err(|error| RlabError::io(root.join("experiments/__init__.py"), error))?;
    let lab = format!(
        "schema_version = 1\n\n[project]\nname = \"{name}\"\n\n[paths]\nruns = \".rlab/runs\"\nartifacts = \".rlab/artifacts\"\ncache = \".rlab/cache\"\n\n[python]\nmodules = [\"experiments\"]\n\n[production]\nstrict = false\n"
    );
    fs::write(root.join("lab.toml"), lab)
        .map_err(|error| RlabError::io(root.join("lab.toml"), error))?;
    Ok(())
}
