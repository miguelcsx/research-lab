from enum import StrEnum


class EntryKind(StrEnum):
    COMPONENT = "component"
    BENCHMARK = "benchmark"
    SUITE = "suite"
    EXPERIMENT = "experiment"
    BASELINE = "baseline"
    EXTERNAL_SUITE = "external_suite"
    DATA_SOURCE = "data_source"
    DATA_TRANSFORM = "data_transform"
    DATA_CHECK = "data_check"
    DATA_METRIC = "data_metric"
    DATASET = "dataset"
    DATA_EXPERIMENT = "data_experiment"
    DATA_ABLATION = "data_ablation"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LauncherKind(StrEnum):
    LOCAL = "local"
    SUBPROCESS = "subprocess"
    DOCKER = "docker"
