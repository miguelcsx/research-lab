use std::io::{BufRead, BufReader};
use std::process::ChildStdout;

use rlab_core::{HostEvent, RlabError, RlabResult};

pub fn read_host_events(stdout: ChildStdout) -> RlabResult<Vec<HostEvent>> {
    let reader = BufReader::new(stdout);
    let mut events = Vec::new();
    for line in reader.lines() {
        let line = line.map_err(|error| RlabError::Host {
            message: format!("failed to read runner output: {error}"),
        })?;
        if line.trim().is_empty() {
            continue;
        }
        let event: HostEvent = serde_json::from_str(&line).map_err(RlabError::serialization)?;
        events.push(event);
    }
    Ok(events)
}
