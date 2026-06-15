mod metrics;
mod runs;

pub use metrics::{compare_metric_arrays, paired_bootstrap, MetricComparison};
pub use runs::{compare_runs, CompareRow};
