use std::fs;
use std::path::Path;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::write_text_atomic;
use crate::run::show_run;

pub fn write_run_report(paths: &ProjectPaths, run_id: &str, output: &Path) -> RlabResult<()> {
    let run = show_run(paths, run_id)?;
    let summary_path = run.path.join("metrics_summary.json");
    let summary = if summary_path.exists() {
        fs::read_to_string(&summary_path).map_err(|error| RlabError::io(&summary_path, error))?
    } else {
        "{}".to_string()
    };
    let report = format!(
        "# Run {run_id}

- operation: `{}`
- name: `{}`
- status: `{}`

## Metrics

```json
{}
```
",
        run.operation,
        run.name,
        run.status.as_str(),
        summary
    );
    write_text_atomic(output, &report)
}
