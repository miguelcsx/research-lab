# Public API reference

The Python package is a thin boundary over Rust-owned behavior. Internal
modules may change; prefer top-level `rlab` imports and methods on
`rlab.Project`.

## Core

```python
rlab.Project
rlab.RuntimeContext
rlab.WorkflowContext
rlab.RunHandle
rlab.RunRecord
rlab.RunQuery
rlab.RunRef
rlab.ArtifactRef
rlab.find_project_root
rlab.load_config
rlab.resolve_config
rlab.apply_overrides
rlab.read_json_manifest
```

## Registry and declarations

```python
rlab.ComponentSpec
rlab.ComponentUse
rlab.ComponentContract
rlab.Requirements
rlab.MissingRequirements
rlab.MissingRequirementsError
rlab.collect_component_requirements
rlab.collect_contracts
rlab.collect_requirements
rlab.missing_requirements
rlab.ref
```

Use methods on `Project` for declarations. Top-level decorators such as
`rlab.experiment`, `rlab.dataset`, and `rlab.component` are not public API.

## Data

```python
rlab.DataBoundary
rlab.DataDecision
rlab.AuditPolicy
rlab.SinkResult
rlab.data_keep
rlab.data_update
rlab.data_drop
rlab.data_boundary
rlab.list_data_documents
rlab.resolve_data_document
rlab.validate_data_documents
rlab.list_datasets
rlab.resolve_dataset
rlab.validate_datasets
```

## Results, workflows, and external tools

```python
rlab.Metric
rlab.ResultBundle
rlab.FileArtifact
rlab.FigureArtifact
rlab.TableArtifact
rlab.LogArtifact
rlab.ResultSchema
rlab.bundle_from_metrics
rlab.Workflow
rlab.WorkflowStep
rlab.ExternalStep
rlab.ExternalCommand
rlab.ExternalResult
rlab.ExternalCommandError
rlab.ExternalWorkspace
rlab.ExternalPath
rlab.BaseAdapter
rlab.AdapterContext
```

`RuntimeContext` exposes resolved run/cache paths, output helpers,
artifact/manifest helpers, progress reporting, `run(target, params)` for child
targets, `external_workspace(name, spec, params)`, and
`run_external(name, command)`.

## Rust-backed runtime utilities

```python
rlab.ArtifactStore
rlab.ArtifactManifest
rlab.CheckpointManager
rlab.CheckpointRecord
rlab.RetentionPolicy
rlab.compare_metric_arrays
rlab.paired_bootstrap
rlab.write_card
rlab.write_markdown_report
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
