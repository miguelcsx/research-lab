from __future__ import annotations


class DataId(str):
    """Validated nominal identifier used by the data recipe API."""

    def __new__(cls, value: str) -> DataId:
        normalized = value.strip()
        if not normalized or any(char.isspace() for char in normalized):
            raise ValueError(f"{cls.__name__} must be non-empty and contain no whitespace")
        return str.__new__(cls, normalized)


class DatasetId(DataId):
    pass


class SourceId(DataId):
    pass


class StageId(DataId):
    pass


class CheckId(DataId):
    pass


class MetricId(DataId):
    pass


class OutputId(DataId):
    pass
