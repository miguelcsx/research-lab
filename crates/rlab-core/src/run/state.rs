use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RunStatus {
    Created,
    Planned,
    Running,
    Completed,
    Failed,
    Cancelled,
    Stale,
    Reproduced,
}

impl RunStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Created => "created",
            Self::Planned => "planned",
            Self::Running => "running",
            Self::Completed => "completed",
            Self::Failed => "failed",
            Self::Cancelled => "cancelled",
            Self::Stale => "stale",
            Self::Reproduced => "reproduced",
        }
    }

    pub fn parse(value: &str) -> RlabResult<Self> {
        match value {
            "created" => Ok(Self::Created),
            "planned" => Ok(Self::Planned),
            "running" => Ok(Self::Running),
            "completed" => Ok(Self::Completed),
            "failed" => Ok(Self::Failed),
            "cancelled" => Ok(Self::Cancelled),
            "stale" => Ok(Self::Stale),
            "reproduced" => Ok(Self::Reproduced),
            _ => Err(RlabError::Run {
                message: format!("unknown run status: {value}"),
            }),
        }
    }

    pub fn can_transition_to(self, next: Self) -> bool {
        matches!(
            (self, next),
            (Self::Created, Self::Planned)
                | (Self::Created, Self::Running)
                | (Self::Planned, Self::Running)
                | (Self::Running, Self::Completed)
                | (Self::Running, Self::Failed)
                | (Self::Running, Self::Cancelled)
                | (Self::Completed, Self::Stale)
                | (Self::Completed, Self::Reproduced)
                | (Self::Failed, Self::Stale)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_transitions() {
        assert!(RunStatus::Created.can_transition_to(RunStatus::Running));
        assert!(RunStatus::Running.can_transition_to(RunStatus::Completed));
        assert!(RunStatus::Running.can_transition_to(RunStatus::Failed));
        assert!(RunStatus::Completed.can_transition_to(RunStatus::Stale));
    }

    #[test]
    fn invalid_transitions() {
        assert!(!RunStatus::Completed.can_transition_to(RunStatus::Running));
        assert!(!RunStatus::Failed.can_transition_to(RunStatus::Completed));
        assert!(!RunStatus::Created.can_transition_to(RunStatus::Completed));
    }

    #[test]
    fn parse_roundtrip() {
        for status in [
            RunStatus::Created,
            RunStatus::Running,
            RunStatus::Completed,
            RunStatus::Failed,
        ] {
            assert_eq!(expect_ok(RunStatus::parse(status.as_str())), status);
        }
    }

    #[test]
    fn parse_unknown_fails() {
        assert!(RunStatus::parse("unknown_status").is_err());
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }
}
