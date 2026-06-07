from enum import StrEnum


class EntryKind(StrEnum):
    COMPONENT = "component"
    BENCHMARK = "benchmark"
    SUITE = "suite"
    EXPERIMENT = "experiment"
    BASELINE = "baseline"
    EXTERNAL_SUITE = "external_suite"
    WORKFLOW = "workflow"
    RESULT_SCHEMA = "result_schema"
    DATA_SOURCE = "data_source"
    DATA_TRANSFORM = "data_transform"
    DATA_CHECK = "data_check"
    DATA_METRIC = "data_metric"
    DATASET = "dataset"
    DATA_EXPERIMENT = "data_experiment"
    DATA_ABLATION = "data_ablation"


class RunStatus(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
    REPRODUCED = "reproduced"


class Direction(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class ArtifactMaturity(StrEnum):
    SCRATCH = "scratch"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    RETRACTED = "retracted"


class ArtifactVisibility(StrEnum):
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"
    PAPER = "paper"


class IdeaStatus(StrEnum):
    IDEA = "idea"
    PLANNED = "planned"
    RUNNING = "running"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PUBLISHED = "published"


class FailureKind(StrEnum):
    CODE_ERROR = "code_error"
    DATA_ERROR = "data_error"
    DEPENDENCY_ERROR = "dependency_error"
    EXTERNAL_COMMAND_ERROR = "external_command_error"
    RESOURCE_ERROR = "resource_error"
    TIMEOUT = "timeout"
    NUMERICAL_INSTABILITY = "numerical_instability"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LauncherKind(StrEnum):
    LOCAL = "local"
    SUBPROCESS = "subprocess"
    DOCKER = "docker"


class DataAvailability(StrEnum):
    AVAILABLE = "available"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    SYNTHETIC = "synthetic"
    SAMPLE_ONLY = "sample_only"
    UNAVAILABLE = "unavailable"
