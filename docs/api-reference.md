# Public API Reference

`rlab` is a runtime execution kernel. Python exposes decorators and context
helpers; Rust owns registry validation, execution, runs, artifacts, cache, and
storage.

## Core Runtime

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

## Runtime Decorators

Use methods on `Project`; there are no top-level decorators.

```python
lab.experiment(name, params=None, **metadata)
lab.study(name, targets=(), params=None, axes=None, seeds=(), **metadata)
lab.workflow(name, steps=(), **metadata)
lab.benchmark(name, target=None, params=None, **metadata)
lab.evaluation(name, params=None, adapter=None, **metadata)
```

Support entries are discoverable but not directly runnable:

```python
lab.adapter(name, **metadata)
lab.loader(name, **metadata)
lab.executor(name, **metadata)
lab.resolver(name, **metadata)
lab.exporter(name, **metadata)
lab.reporter(name, **metadata)
lab.notifier(name, **metadata)
```

## Context And Results

```python
ctx.params(MyParams)
ctx.params_dict()
ctx.param("name", default)
ctx.log_metric("loss", 0.2)
ctx.log_metrics({"loss": 0.2})
ctx.output_path("model.pt")
ctx.save_artifact(path, name="checkpoint", kind="model")
ctx.run("experiment:child", {"seed": 1})
ctx.run_external("tool", command)
```

```python
rlab.Metric
rlab.ResultBundle
rlab.FileArtifact
rlab.FigureArtifact
rlab.TableArtifact
rlab.LogArtifact
rlab.bundle_from_metrics
```

## Runtime Storage And External Tools

```python
rlab.ArtifactStore
rlab.ArtifactManifest
rlab.CacheEntry
rlab.list_cache
rlab.cache_path
rlab.cache_size
rlab.ExternalCommand
rlab.ExternalResult
rlab.ExternalWorkspace
rlab.ExternalPath
rlab.ExternalCommandError
rlab.BaseAdapter
rlab.AdapterContext
```

## Data Decisions

Only runtime-neutral decisions are public:

```python
`rlab` has no built-in data decision API. Projects model filtering, grouping,
deduplication, records, and data decisions in their own code.
```

## Removed From Public API

`rlab` does not expose components, builders, datasets, pipelines, filters,
data checks, result schemas, or scientific/data declaration helpers.
Project code owns those definitions behind runtime decorators.
