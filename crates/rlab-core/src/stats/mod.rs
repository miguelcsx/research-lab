mod descriptive;
mod hypothesis;

pub use descriptive::{describe_array, DescriptiveStats};
pub use hypothesis::{compare_samples, SampleComparison};
pub use crate::compare::{compare_metric_arrays, MetricComparison};
