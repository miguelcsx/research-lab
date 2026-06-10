use serde_json::Value;

use super::model::DataDecision;
const SCHEMA_VERSION: u32 = 1;

pub fn data_keep(record: Value) -> DataDecision {
    DataDecision::Keep { schema_version: SCHEMA_VERSION, record }
}

pub fn data_update(record: Value, reason: Option<String>) -> DataDecision {
    DataDecision::Update { schema_version: SCHEMA_VERSION, record, reason }
}

pub fn data_drop(reason: String) -> DataDecision {
    DataDecision::Drop { schema_version: SCHEMA_VERSION, reason }
}

pub fn data_boundary(value: Value, kind: String) -> DataDecision {
    DataDecision::Boundary { schema_version: SCHEMA_VERSION, value, kind }
}
