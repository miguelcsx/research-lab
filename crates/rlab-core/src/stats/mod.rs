mod descriptive;
mod hypothesis;

pub use crate::compare::{compare_metric_arrays, MetricComparison};
pub use descriptive::{describe_array, DescriptiveStats};
pub use hypothesis::{compare_samples, SampleComparison};
