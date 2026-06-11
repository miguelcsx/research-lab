use serde::{Deserialize, Serialize};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseManifest {
    pub schema_version: u32,
    pub name: String,
    pub license: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseCompatibilitySummary {
    pub schema_version: u32,
    pub compatible: bool,
    pub warnings: Vec<String>,
}

pub fn check_compatibility(manifests: &[LicenseManifest]) -> LicenseCompatibilitySummary {
    let warnings = manifests
        .iter()
        .filter_map(|manifest| {
            let license = manifest.license.to_lowercase();
            if license.contains("non-commercial") || license.contains("nc") {
                Some(format!("{} uses a non-commercial license", manifest.name))
            } else if license.trim().is_empty() || license == "unknown" {
                Some(format!("{} has an unknown license", manifest.name))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();
    LicenseCompatibilitySummary {
        schema_version: SCHEMA_VERSION,
        compatible: warnings.is_empty(),
        warnings,
    }
}
