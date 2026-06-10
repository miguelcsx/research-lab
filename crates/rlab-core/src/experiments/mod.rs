pub mod matrix;
pub mod model;
pub mod planner;
pub mod retry;

pub use matrix::{Choice, Distribution, Grid, MatrixValue, Sample};
pub use model::{ExperimentJob, ExperimentPlan, ExperimentSpec};
pub use planner::plan_experiment;
pub use retry::{FailureKind, RetryPolicy};
