# Public API reference

This page summarizes the intended public API. Internal modules may change.

## Top-level package

```python
import rlab
```

## Core

```python
rlab.Project
rlab.RuntimeContext
rlab.WorkflowContext
```

## Results

```python
rlab.Metric
rlab.ResultBundle
rlab.FileArtifact
rlab.FigureArtifact
rlab.TableArtifact
rlab.LogArtifact
rlab.ResultSchema
rlab.bundle_from_metrics
```

## Manifests

```python
rlab.RunManifest
rlab.ArtifactManifest
rlab.ModelManifest
rlab.DatasetManifest
```

## Data

```python
rlab.DataContext
rlab.DataSource
rlab.DataAction
rlab.DataDecision
rlab.DataBoundary
rlab.ComponentUse
rlab.PipelineSpec
rlab.DatasetSpec
rlab.AuditPolicy
rlab.DataCheck
rlab.DataMetric
rlab.DataSink
rlab.CheckResult
rlab.SinkResult
rlab.DataAblation
rlab.DataExperiment
rlab.materialize
rlab.data_keep
rlab.data_update
rlab.data_drop
rlab.data_boundary
rlab.patterns
rlab.substitute
rlab.classify
rlab.predicate
rlab.threshold
```

## Workflows and external commands

```python
rlab.Workflow
rlab.WorkflowStep
rlab.ExternalStep
rlab.define_workflow
rlab.ExternalCommand
rlab.ExternalResult
rlab.ExternalCommandError
rlab.ExternalPath
rlab.ExternalWorkspace
rlab.BaseAdapter
rlab.AdapterContext
rlab.AdapterValidationError
```

`RuntimeContext` exposes resolved `run_dir`, `cache_dir`, `output_dir`,
`external_workspace(name, spec, params)`, and `run_external(name, command)`.

## Benchmarks and evaluations

```python
rlab.BenchmarkContext
rlab.BenchmarkResult
rlab.BenchmarkSpec
rlab.EvaluationSuite
rlab.EvaluationTask
rlab.EvaluationResult
```

## Experiments and studies

```python
rlab.Experiment
rlab.ExperimentResult
rlab.RetryPolicy
rlab.Study
rlab.StudyPlan
```

## Matrix helpers

```python
rlab.Grid
rlab.Sample
rlab.factor
rlab.grid
rlab.log_uniform
rlab.uniform
rlab.choice
```

## Governance, baselines, units, stats

```python
rlab.Assumption
rlab.Threat
rlab.BaselineEntry
rlab.BaselineStore
rlab.Unit
rlab.UnitRegistry
rlab.BudgetEstimate
rlab.estimate_required_repetitions
rlab.estimate_budget
rlab.MetricComparison
rlab.compare_metric_arrays
rlab.compare_runs
```

## Not public

The following must not exist as top-level decorators:

```python
rlab.experiment
rlab.study
rlab.workflow
rlab.evaluation
rlab.component
rlab.benchmark
rlab.source
rlab.transform
rlab.filter
rlab.group
rlab.dedup
rlab.sink
rlab.check
rlab.metric
rlab.pipeline
rlab.dataset
rlab.adapter
rlab.result_schema
```

Use methods on `Project` instead.
