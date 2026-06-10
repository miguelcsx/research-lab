use std::path::{Path, PathBuf};

pub fn find_lockfile(root: &Path) -> Option<PathBuf> {
    ["uv.lock", "Cargo.lock", "poetry.lock", "pdm.lock"]
        .iter()
        .map(|name| root.join(name))
        .find(|path| path.exists())
}
