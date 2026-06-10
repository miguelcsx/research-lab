
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};

use fs2::FileExt;

use crate::error::{RlabError, RlabResult};

pub const RUN_LOCK_FILE: &str = ".rlab.lock";

#[derive(Debug)]
pub struct RunLock {
    path: PathBuf,
    file: File,
}

impl RunLock {
    pub fn acquire(run_dir: &Path) -> RlabResult<Self> {
        let path = run_dir.join(RUN_LOCK_FILE);
        let file = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(false)
            .open(&path)
            .map_err(|error| RlabError::io(&path, error))?;
        file.try_lock_exclusive().map_err(|error| RlabError::Run {
            message: format!("run directory is already locked or unavailable: {} ({error})", run_dir.display()),
        })?;
        Ok(Self { path, file })
    }
}

impl Drop for RunLock {
    fn drop(&mut self) {
        let _ = self.file.unlock();
        let _ = fs::remove_file(&self.path);
    }
}
