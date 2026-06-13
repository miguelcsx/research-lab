use std::path::PathBuf;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum RlabError {
    #[error("configuration error: {message}")]
    Config { message: String },
    #[error("registry error: {message}")]
    Registry { message: String },
    #[error("invalid reference: {message}")]
    Reference { message: String },
    #[error("run error: {message}")]
    Run { message: String },
    #[error("artifact error: {message}")]
    Artifact { message: String },
    #[error("host protocol error: {message}")]
    Host { message: String },
    #[error("validation error: {message}")]
    Validation { message: String },
    #[error("not found: {subject}")]
    NotFound { subject: String },
    #[error("unsupported feature: {feature}")]
    Unsupported { feature: String },
    #[error("io error at {path}: {message}")]
    Io { path: PathBuf, message: String },
    #[error("serialization error: {message}")]
    Serialization { message: String },
}

pub type RlabResult<T> = Result<T, RlabError>;

impl RlabError {
    pub fn io(path: impl Into<PathBuf>, source: std::io::Error) -> Self {
        Self::Io {
            path: path.into(),
            message: source.to_string(),
        }
    }

    pub fn serialization(source: impl std::fmt::Display) -> Self {
        Self::Serialization {
            message: source.to_string(),
        }
    }

    pub fn validation(message: impl Into<String>) -> Self {
        Self::Validation {
            message: message.into(),
        }
    }

    pub fn registry(message: impl Into<String>) -> Self {
        Self::Registry {
            message: message.into(),
        }
    }

    pub fn config(message: impl Into<String>) -> Self {
        Self::Config {
            message: message.into(),
        }
    }
}
