from __future__ import annotations

import pytest

from rlab.governance import (
    LabPolicy,
    LicenseManifest,
    check_compatibility,
    redact_secrets,
    scan_for_pii,
    scan_for_secrets,
)
from rlab.plan import estimate_budget, estimate_required_repetitions


def test_plan_helpers_are_rust_backed() -> None:
    estimate = estimate_budget(3, seconds_per_job=2.5, storage_gb_per_job=1.25)

    assert estimate.jobs == 3
    assert estimate.total_seconds == 7.5
    assert estimate.total_storage_gb == 3.75
    assert estimate_budget(1, 2.0, 3.0).total_storage_gb == 3.0
    assert estimate_required_repetitions(0.5, 1.0, 0.05, 0.8) >= 1

    with pytest.raises(ValueError):
        estimate_budget(0, 1.0, 1.0)


def test_governance_helpers_are_rust_backed() -> None:
    env = {"API_TOKEN": "secret", "PATH": "/bin"}

    assert redact_secrets(env) == {"API_TOKEN": "<redacted>", "PATH": "/bin"}
    assert scan_for_secrets("API_TOKEN=secret")[0].key == "API_TOKEN"
    assert scan_for_pii("contact test@example.com from 127.0.0.1")[0].kind == "email"

    summary = check_compatibility(
        [LicenseManifest("corpus", "unknown"), LicenseManifest("model", "MIT")]
    )
    assert not summary.compatible
    assert summary.warnings == ["corpus has an unknown license"]

    violations = LabPolicy().check_env(env)
    assert violations[0].subject == "API_TOKEN"
    assert LabPolicy(("TOKEN",)).check_env(env)[0].rule == "forbidden_env_patterns"
