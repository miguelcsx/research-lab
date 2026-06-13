use serde::{Deserialize, Serialize};

use crate::error::RlabResult;
use crate::registry::{Registry, RegistryKind};

use super::model::{AdapterCapability, AdapterDescriptor, AdapterHealth, AdapterStatus};
use super::validation::validate_adapter_descriptor;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterInventory {
    pub schema_version: u32,
    pub adapters: Vec<AdapterHealth>,
}

pub fn adapter_inventory(registry: &Registry) -> RlabResult<AdapterInventory> {
    let mut adapters = Vec::new();
    for record in registry.records_by_kind(RegistryKind::ADAPTER) {
        let declared_capabilities = record
            .metadata
            .get("capabilities")
            .and_then(|value| value.as_array())
            .map(|values| {
                values
                    .iter()
                    .filter_map(|value| value.as_str())
                    .filter_map(parse_capability)
                    .collect::<Vec<_>>()
            });
        let capabilities = match declared_capabilities {
            Some(values) if !values.is_empty() => values,
            Some(_) | None => vec![AdapterCapability::ExternalCommand],
        };
        let descriptor = AdapterDescriptor {
            schema_version: SCHEMA_VERSION,
            name: record.name.clone(),
            module: record.module.clone(),
            qualname: record.qualname.clone(),
            source: record.source.clone(),
            capabilities,
            description: record.description.clone(),
        };
        let findings = match validate_adapter_descriptor(&descriptor) {
            Ok(()) => Vec::new(),
            Err(error) => vec![error.to_string()],
        };
        let status = if findings.is_empty() {
            AdapterStatus::Declared
        } else {
            AdapterStatus::Invalid
        };
        adapters.push(AdapterHealth {
            schema_version: SCHEMA_VERSION,
            descriptor,
            status,
            findings,
        });
    }
    Ok(AdapterInventory {
        schema_version: SCHEMA_VERSION,
        adapters,
    })
}

fn parse_capability(value: &str) -> Option<AdapterCapability> {
    match value {
        "external_command" => Some(AdapterCapability::ExternalCommand),
        "external_evaluation" => Some(AdapterCapability::ExternalEvaluation),
        "repository_checkout" => Some(AdapterCapability::RepositoryCheckout),
        "artifact_mapping" => Some(AdapterCapability::ArtifactMapping),
        "custom_parser" => Some(AdapterCapability::CustomParser),
        _ => None,
    }
}
