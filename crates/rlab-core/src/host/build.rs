use std::collections::BTreeMap;

use serde_json::{json, Value};

use crate::result::Metric;
use crate::{RlabError, RlabResult};

use super::{ArtifactEvent, HostEvent, LogEvent, MetricEvent, ProtocolVersion};

const RESULT_SCHEMA_VERSION: u32 = 1;

pub fn execution_events(
    request_id: &str,
    metrics: &BTreeMap<String, f64>,
    artifacts: &[Value],
    logs: &[String],
    result: Value,
) -> Vec<HostEvent> {
    let mut events = Vec::new();
    events.extend(
        metrics
            .iter()
            .map(|(name, value)| metric_event(request_id, name.clone(), *value)),
    );
    events.extend(artifacts.iter().cloned().map(|artifact| {
        HostEvent::Artifact(ArtifactEvent {
            protocol_version: ProtocolVersion::current(),
            request_id: request_id.to_string(),
            artifact,
        })
    }));
    events.extend(logs.iter().cloned().map(|message| {
        HostEvent::Log(LogEvent {
            protocol_version: ProtocolVersion::current(),
            request_id: request_id.to_string(),
            message,
        })
    }));
    events.extend(
        flatten_numbers(&result, "")
            .into_iter()
            .map(|(name, value)| metric_event(request_id, name, value)),
    );
    events.push(HostEvent::Completed {
        protocol_version: ProtocolVersion::current(),
        request_id: request_id.to_string(),
        result: json!({
            "schema_version": RESULT_SCHEMA_VERSION,
            "data": result,
        }),
    });
    events
}

pub fn failed_event(
    request_id: &str,
    kind: &str,
    message: &str,
    safe_traceback: &str,
    source: &str,
) -> HostEvent {
    HostEvent::Failed {
        protocol_version: ProtocolVersion::current(),
        request_id: request_id.to_string(),
        error: json!({
            "schema_version": RESULT_SCHEMA_VERSION,
            "kind": kind,
            "message": message,
            "safe_traceback": safe_traceback,
            "source": source,
        }),
    }
}

pub fn event_lines(events: &[HostEvent]) -> RlabResult<Vec<String>> {
    events
        .iter()
        .map(|event| serde_json::to_string(event).map_err(RlabError::serialization))
        .collect()
}

fn metric_event(request_id: &str, name: String, value: f64) -> HostEvent {
    HostEvent::Metric(MetricEvent {
        protocol_version: ProtocolVersion::current(),
        request_id: request_id.to_string(),
        metric: Metric::new(name, value, None, None),
    })
}

fn flatten_numbers(value: &Value, prefix: &str) -> Vec<(String, f64)> {
    match value {
        Value::Number(number) => number
            .as_f64()
            .filter(|_| !prefix.is_empty())
            .map(|value| vec![(prefix.to_string(), value)])
            .unwrap_or_default(),
        Value::Object(object) => object
            .iter()
            .flat_map(|(key, child)| {
                let name = child_name(prefix, key);
                flatten_numbers(child, &name)
            })
            .collect(),
        Value::Array(values) => values
            .iter()
            .enumerate()
            .flat_map(|(index, child)| {
                let name = child_name(prefix, &index.to_string());
                flatten_numbers(child, &name)
            })
            .collect(),
        _ => Vec::new(),
    }
}

fn child_name(prefix: &str, name: &str) -> String {
    if prefix.is_empty() {
        name.to_string()
    } else {
        format!("{prefix}.{name}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_context_events_and_result_metrics() {
        let mut metrics = BTreeMap::new();
        metrics.insert("loss".to_string(), 0.4);
        let events = execution_events(
            "r1",
            &metrics,
            &[json!({"path": "model.bin"})],
            &["hello".to_string()],
            json!({"accuracy": 0.9, "nested": {"count": 2}, "ok": true}),
        );

        assert_eq!(events.len(), 6);
        assert!(matches!(events[0], HostEvent::Metric(_)));
        assert!(matches!(events[1], HostEvent::Artifact(_)));
        assert!(matches!(events[2], HostEvent::Log(_)));
        assert!(matches!(events[5], HostEvent::Completed { .. }));
    }

    #[test]
    fn formats_failed_event_as_host_error() {
        let event = failed_event("r1", "python_exception", "boom", "trace", "rlab._runner");
        let HostEvent::Failed { error, .. } = event else {
            panic!("expected failed event");
        };

        assert_eq!(error["kind"], "python_exception");
        assert_eq!(error["message"], "boom");
    }
}
