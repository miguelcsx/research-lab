# Python runner protocol

Rust starts the Python runner only when Python project code is required.

```bash
python -m rlab._runner
```

The transport is JSON Lines over stdin/stdout.

## Request envelope

```json
{
  "protocol_version": 1,
  "request_id": "req_01HX...",
  "command": "execute",
  "project_root": "/abs/project",
  "modules": ["experiments"],
  "target": {
    "kind": "experiment",
    "name": "sweep"
  },
  "run_id": "run_01HX...",
  "params": {},
  "seed": null,
  "strict": false,
  "environment": {
    "python_executable": "/abs/.venv/bin/python",
    "python_version": "3.12.4",
    "cwd": "/abs/project"
  }
}
```

## Commands

```text
discover
validate_imports
execute
```

## Events

The runner emits events. Rust validates all of them.

Supported event types:

```text
registry_record
metric
artifact
log
warning
error
completed
failed
batch
```

## Registry record event

```json
{
  "protocol_version": 1,
  "request_id": "req_01HX...",
  "event_type": "registry_record",
  "record": {
    "schema_version": 1,
    "kind": "experiment",
    "name": "sweep",
    "version": "1",
    "module": "experiments.sweep",
    "qualname": "sweep",
    "source": "experiments/sweep.py",
    "tags": [],
    "description": "",
    "metadata": {}
  }
}
```

## Metric event

```json
{
  "protocol_version": 1,
  "request_id": "req_01HX...",
  "event_type": "metric",
  "metric": {
    "schema_version": 1,
    "name": "loss",
    "value": 0.2,
    "unit": null,
    "direction": null
  }
}
```

## Completion event

```json
{
  "protocol_version": 1,
  "request_id": "req_01HX...",
  "event_type": "completed",
  "result": {
    "schema_version": 1,
    "data": {"ok": true}
  }
}
```

Python never writes final run state directly. Rust owns final persistence and status transitions.
