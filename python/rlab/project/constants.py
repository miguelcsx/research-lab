"""Project registry constants."""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final = 1
DEFAULT_VERSION: Final = "1"

STRICT_ENV_VAR: Final = "RLAB_RUNNER_STRICT"
STRICT_ENABLED: Final = "1"
GENERATED_MODULE: Final = "rlab.generated"

KEY_SCHEMA_VERSION: Final = "schema_version"
KEY_KIND: Final = "kind"
KEY_NAME: Final = "name"
KEY_VERSION: Final = "version"
KEY_MODULE: Final = "module"
KEY_QUALNAME: Final = "qualname"
KEY_SOURCE: Final = "source"
KEY_TAGS: Final = "tags"
KEY_DESCRIPTION: Final = "description"
KEY_METADATA: Final = "metadata"
KEY_STEPS: Final = "steps"
KEY_TARGET: Final = "target"
KEY_TARGETS: Final = "targets"
KEY_SUITE: Final = "suite"
KEY_TASK: Final = "task"
KEY_ADAPTER: Final = "adapter"
KEY_AXES: Final = "axes"
KEY_SEEDS: Final = "seeds"
KEY_PARAMS: Final = "params"
KEY_PARAM_SCHEMA: Final = "param_schema"
KEY_REF: Final = "ref"
KEY_REFERENCE: Final = "reference"
KEY_EXPERIMENT_TYPE: Final = "experiment_type"

KIND_EXPERIMENT: Final = "experiment"
KIND_WORKFLOW: Final = "workflow"
KIND_STUDY: Final = "study"
KIND_BENCHMARK: Final = "benchmark"
KIND_EVALUATION: Final = "evaluation"
KIND_ADAPTER: Final = "adapter"
KIND_LOADER: Final = "loader"
KIND_EXECUTOR: Final = "executor"
KIND_RESOLVER: Final = "resolver"
KIND_EXPORTER: Final = "exporter"
KIND_REPORTER: Final = "reporter"
KIND_NOTIFIER: Final = "notifier"

TYPE_OBJECT: Final = "object"
TYPE_ARRAY: Final = "array"
TYPE_STRING: Final = "string"
TYPE_BOOLEAN: Final = "boolean"
TYPE_INTEGER: Final = "integer"
TYPE_NUMBER: Final = "number"
TYPE_NULL: Final = "null"
FORMAT_PATH: Final = "path"

JSON_TYPE_KEY: Final = "type"
JSON_FORMAT_KEY: Final = "format"
JSON_ENUM_KEY: Final = "enum"
JSON_ITEMS_KEY: Final = "items"
JSON_ANY_OF_KEY: Final = "anyOf"
JSON_PROPERTIES_KEY: Final = "properties"
JSON_REQUIRED_KEY: Final = "required"
JSON_ADDITIONAL_PROPERTIES_KEY: Final = "additionalProperties"
JSON_DEFAULT_KEY: Final = "default"

SENTINEL_UNSTABLE_SOURCE_PREFIX: Final = "<"
QUALNAME_LAMBDA: Final = "<lambda>"
QUALNAME_LOCALS: Final = "<locals>"

REFERENCE_SEPARATOR: Final = ":"
REFERENCE_SEPARATOR_COUNT: Final = 1

VALID_NAME_EXTRA_CHARS: Final = frozenset("._-:")
SIMPLE_JSON_TYPES: Final = (str, int, float, bool, type(None))

ERROR_KIND_NAME_REQUIRED: Final = "registry kind and name are required"
ERROR_INVALID_NAME: Final = "invalid registry name {name!r}"
ERROR_DUPLICATE_DECLARATION: Final = "duplicate registry declaration: {kind}:{name}"
ERROR_UNSTABLE_STRICT: Final = "unstable strict declaration for {kind}:{name}"
ERROR_WORKFLOW_RECORD_MISSING: Final = (
    "workflow record not found while adding step: {workflow_name}"
)
ERROR_DUPLICATE_WORKFLOW_STEP: Final = (
    "duplicate workflow step: {workflow_name}:{step_name}"
)
ERROR_WORKFLOW_STEPS_INVALID: Final = (
    "workflow {workflow_name} has invalid steps metadata"
)
ERROR_NO_CALLABLE: Final = "no callable registered for {kind}:{name}"
ERROR_NO_RECORD: Final = "no registry record for {kind}:{name}"
ERROR_SCHEMA_JSON: Final = "{label} must define model_json_schema()"
ERROR_SCHEMA_DICT: Final = "{label} model_json_schema() must return a dict"
ERROR_SCHEMA_VALIDATE: Final = (
    "params schema for {kind}:{name} must define model_validate()"
)
ERROR_JSON_SERIALIZABLE: Final = "{label} must be JSON serializable"
ERROR_VALUE_JSON_SERIALIZABLE: Final = "value is not JSON serializable: {type_name}"
ERROR_STRING_LIST: Final = "{label} must be a list of strings"
ERROR_OBJECT_SEQUENCE: Final = "{label} must be a sequence"
