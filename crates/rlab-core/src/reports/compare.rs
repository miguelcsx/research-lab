use std::path::Path;

use crate::compare::compare_runs;
use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::write_text_atomic;

pub fn write_compare_report(paths: &ProjectPaths, output: &Path) -> RlabResult<()> {
    let rows = compare_runs(paths, None)?;
    let json = serde_json::to_string_pretty(&rows).map_err(RlabError::serialization)?;
    write_text_atomic(
        output,
        &format!(
            "# Run comparison

```json
{json}
```
"
        ),
    )
}
