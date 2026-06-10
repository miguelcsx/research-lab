mod inventory;
mod model;
mod validation;

pub use inventory::{adapter_inventory, AdapterInventory};
pub use model::{AdapterCapability, AdapterDescriptor, AdapterHealth, AdapterStatus};
pub use validation::validate_adapter_descriptor;
