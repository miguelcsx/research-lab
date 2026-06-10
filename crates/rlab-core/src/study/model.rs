use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StudyOutcome {
    pub schema_version: u32,
    pub name: String,
    pub metric: String,
    pub direction: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StudyPlan {
    pub schema_version: u32,
    pub question: String,
    pub experiments: Vec<String>,
    pub outcomes: Vec<StudyOutcome>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Study {
    pub schema_version: u32,
    pub name: String,
    pub plan: StudyPlan,
}
