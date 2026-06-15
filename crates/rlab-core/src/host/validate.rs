use crate::error::{RlabError, RlabResult};
use crate::registry::validate_registry_record;

use super::event::HostEvent;
use super::protocol::PROTOCOL_VERSION_NUMBER;

pub fn validate_event(event: &HostEvent) -> RlabResult<()> {
    match event {
        HostEvent::RegistryRecord(value) => {
            validate_protocol(value.protocol_version.0)?;
            validate_registry_record(&value.record)
        }
        HostEvent::Metric(value) => {
            validate_protocol(value.protocol_version.0)?;
            if value.metric.name.trim().is_empty() {
                return Err(RlabError::Host {
                    message: "metric name cannot be empty".to_string(),
                });
            }
            Ok(())
        }
        HostEvent::Artifact(value) => validate_protocol(value.protocol_version.0),
        HostEvent::Log(value) | HostEvent::Warning(value) | HostEvent::Error(value) => {
            validate_protocol(value.protocol_version.0)
        }
        HostEvent::Progress(value) => validate_protocol(value.protocol_version.0),
        HostEvent::Completed {
            protocol_version, ..
        }
        | HostEvent::Failed {
            protocol_version, ..
        } => validate_protocol(protocol_version.0),
        HostEvent::Batch {
            protocol_version,
            events,
            ..
        } => {
            validate_protocol(protocol_version.0)?;
            for nested in events {
                validate_event(nested)?;
            }
            Ok(())
        }
    }
}

fn validate_protocol(version: u32) -> RlabResult<()> {
    if version != PROTOCOL_VERSION_NUMBER {
        return Err(RlabError::Host {
            message: format!("unsupported protocol version: {version}"),
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::host::event::{LogEvent, MetricEvent};
    use crate::host::protocol::{ProtocolVersion, PROTOCOL_VERSION_NUMBER};
    use crate::result::Metric;

    fn current_version() -> ProtocolVersion {
        ProtocolVersion(PROTOCOL_VERSION_NUMBER)
    }

    fn wrong_version() -> ProtocolVersion {
        ProtocolVersion(PROTOCOL_VERSION_NUMBER + 1)
    }

    #[test]
    fn valid_log_event_passes() {
        let event = HostEvent::Log(LogEvent {
            protocol_version: current_version(),
            request_id: "r1".to_string(),
            message: "hello".to_string(),
        });
        assert!(validate_event(&event).is_ok());
    }

    #[test]
    fn wrong_protocol_version_fails() {
        let event = HostEvent::Log(LogEvent {
            protocol_version: wrong_version(),
            request_id: "r1".to_string(),
            message: "hello".to_string(),
        });
        assert!(validate_event(&event).is_err());
    }

    #[test]
    fn metric_event_with_empty_name_fails() {
        let event = HostEvent::Metric(MetricEvent {
            protocol_version: current_version(),
            request_id: "r1".to_string(),
            metric: Metric::new("  ".to_string(), 1.0, None, None),
        });
        assert!(validate_event(&event).is_err());
    }

    #[test]
    fn completed_event_passes() {
        let event = HostEvent::Completed {
            protocol_version: current_version(),
            request_id: "r1".to_string(),
            result: serde_json::json!({}),
        };
        assert!(validate_event(&event).is_ok());
    }
}
