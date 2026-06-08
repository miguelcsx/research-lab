# Public API reference

Most users should import from `rlab` directly.

```python
import rlab
```

The top-level package re-exports common models, decorators, helpers, and result types.

## Core context

```python
rlab.RuntimeContext
```

Use inside execution code to access config, paths, registry, params, seed, resources, and run helpers.

## Experiments

```python
rlab.Experiment
rlab.ExperimentResult
rlab.RetryPolicy
rlab.Grid
rlab.Sample
rlab.factor
rlab.grid
rlab.log_uniform
rlab.uniform
rlab.choice
```

## Benchmarks

```python
rlab.BenchmarkContext
rlab.BenchmarkResult
```

## Evaluations

```python
rlab.EvaluationSuite
rlab.EvaluationTask
rlab.EvaluationResult
```

## Data

```python
rlab.DataPipeline
rlab.DataBuildResult
rlab.DataContext
rlab.DataCheckResult
rlab.DataAblation
rlab.DataExperiment
rlab.DatasetManifest
```

## Workflows

```python
rlab.Workflow
rlab.WorkflowStep
rlab.ExternalStep
```

## External commands

```python
rlab.ExternalCommand
rlab.ExternalEvaluation
rlab.ExternalResult
```

## Results

```python
rlab.ResultBundle
rlab.Metric
rlab.FigureArtifact
rlab.TableArtifact
rlab.FileArtifact
rlab.LogArtifact
rlab.ResultSchema
rlab.bundle_from_metrics
```

## Manifests

```python
rlab.ArtifactManifest
rlab.ModelManifest
rlab.RunManifest
```

## Baselines

```python
rlab.BaselineEntry
rlab.BaselineStore
```

## Power and budget

```python
rlab.BudgetEstimate
rlab.estimate_required_repetitions
rlab.estimate_budget
```

## Assumptions and threats

```python
rlab.Assumption
rlab.Threat
```

## Units

```python
rlab.Unit
rlab.UnitRegistry
```

## Decorators

```python
rlab.component
rlab.benchmark
rlab.suite
rlab.external_suite
rlab.experiment
rlab.baseline
rlab.workflow
rlab.workflow_step
rlab.result_schema
rlab.data_source
rlab.data_transform
rlab.data_check
rlab.data_metric
rlab.dataset_variant
rlab.data_experiment
rlab.data_ablation
```

## Lower-level imports

Use lower-level imports when you need infrastructure services directly:

```python
from rlab.context.factory import build_runtime
from rlab.artifacts.service import promote_path
from rlab.runs.reader import RunReader
from rlab.runs.writer import RunWriter
from rlab.reproducibility.service import reproduce
from rlab.reporting.compare import compare_runs
from rlab.search.index import SearchIndex
```

## Stability expectation

The top-level `rlab` API is the user-facing API. Internal modules are organized and typed, but projects should prefer top-level imports unless they intentionally need lower-level services.
