mod policy;
mod production;

pub use policy::{ProductionPolicy, StrictMode};
pub use production::validate_record_for_production;
