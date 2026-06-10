use std::path::Path;

use crate::error::RlabResult;
use crate::fs::write_text_atomic;

pub fn write_command(path: &Path, command: &[String]) -> RlabResult<()> {
    write_text_atomic(path, &command.join(" "))
}
