mod kind;
mod safe;

pub use kind::{RlabError, RlabResult};
pub use safe::{redact_secrets, SafeMessage};
