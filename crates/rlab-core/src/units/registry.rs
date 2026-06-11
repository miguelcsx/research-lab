use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Unit {
    pub name: String,
    pub symbol: String,
    pub dimension: String,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct UnitRegistry {
    pub schema_version: u32,
    pub units: BTreeMap<String, Unit>,
}

impl UnitRegistry {
    pub fn new() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            units: BTreeMap::new(),
        }
    }

    pub fn insert(&mut self, unit: Unit) -> RlabResult<()> {
        if unit.name.trim().is_empty()
            || unit.symbol.trim().is_empty()
            || unit.dimension.trim().is_empty()
        {
            return Err(RlabError::Validation {
                message: "unit name, symbol, and dimension are required".to_string(),
            });
        }
        self.units.insert(unit.symbol.clone(), unit);
        Ok(())
    }
}
