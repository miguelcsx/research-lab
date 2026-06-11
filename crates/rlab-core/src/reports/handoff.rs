use std::path::PathBuf;

use crate::config::ProjectPaths;
use crate::error::RlabResult;
use crate::fs::write_text_atomic;
use crate::run::show_run;

pub fn write_handoff(paths: &ProjectPaths, run_id: &str, recipient: &str) -> RlabResult<PathBuf> {
    let run = show_run(paths, run_id)?;
    let path = run.path.join("handoff.md");
    let body = format!(
        "# Handoff for {run_id}

Recipient: {recipient}

## Context

Run `{}` executed `{}`.

## Reproduce

```bash
rlab reproduce {}
```

## Known issues

- None recorded.

## Suggested next experiments

- Review metrics and compare against current baseline.
",
        run.name,
        run.operation,
        run.path.display()
    );
    write_text_atomic(&path, &body)?;
    Ok(path)
}
