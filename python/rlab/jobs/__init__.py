"""Rust-backed job models."""

from typing import Literal, TypeAlias

from rlab._rlab import JobRecord

JobStatus: TypeAlias = Literal["running", "completed", "failed", "cancelled"]

__all__ = ["JobRecord", "JobStatus"]
