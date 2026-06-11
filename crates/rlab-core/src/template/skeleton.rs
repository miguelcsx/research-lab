use std::fs;
use std::path::Path;

use crate::error::{RlabError, RlabResult};
use crate::fs::write_text_atomic;

pub fn write_experiment_skeleton(root: &Path, name: &str) -> RlabResult<()> {
    let experiments = root.join("experiments");
    fs::create_dir_all(&experiments).map_err(|error| RlabError::io(&experiments, error))?;
    let module_path = experiments.join(format!("{name}.py"));
    if module_path.exists() {
        return Err(RlabError::Validation {
            message: format!("skeleton already exists: {}", module_path.display()),
        });
    }
    let content = format!(
        "import rlab\n\nlab = rlab.Project()\n\n@lab.experiment(\"{name}\")\ndef {name}(ctx):\n    ctx.log_metric(\"loss\", 0.0)\n    return {{\"ok\": True}}\n"
    );
    write_text_atomic(&module_path, &content)
}
