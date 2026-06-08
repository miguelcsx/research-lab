from __future__ import annotations

from pathlib import Path

from rlab.governance.license import LicenseManifest, check_compatibility
from rlab.governance.pii import scan_for_pii
from rlab.governance.policy import LabPolicy
from rlab.governance.secrets import redact_secrets, scan_for_secrets


def test_policy_defaults_load_and_env_checks(tmp_path: Path) -> None:
    default_policy = LabPolicy.load(tmp_path)
    assert not default_policy.require_hypothesis
    assert LabPolicy().check_env({"HF_TOKEN": "abc", "PATH": "/usr/bin"})
    assert LabPolicy().check_env({"PATH": "/usr/bin", "HOME": "/home/user"}) == []

    (tmp_path / "lab.policy.toml").write_text(
        "[required]\nrequire_hypothesis = true\nrequire_clean_git_for_promotion = true\n",
        encoding="utf-8",
    )
    loaded = LabPolicy.load(tmp_path)
    assert loaded.require_hypothesis
    assert loaded.require_clean_git_for_promotion


def test_secret_redaction_and_detection() -> None:
    redacted = redact_secrets(
        {"PATH": "/usr/bin", "HF_TOKEN": "hf_secret123", "WANDB_API_KEY": "abc"}
    )
    assert redacted["PATH"] == "/usr/bin"
    assert redacted["HF_TOKEN"] == "[REDACTED]"
    assert redact_secrets({"MY_TOKEN": "keep_me"}, allowlist=("MY_TOKEN",))["MY_TOKEN"] == "keep_me"
    assert len(scan_for_secrets("export HF_TOKEN=abc123\nAPI_KEY=secret")) >= 2


def test_pii_scanner() -> None:
    hits = scan_for_pii("Contact user@example.com. SSN: 123-45-6789.")
    kinds = {hit.kind for hit in hits}
    assert "email" in kinds
    assert "ssn" in kinds
    assert not scan_for_pii("Just regular text here.")


def test_license_compatibility() -> None:
    permissive = (
        LicenseManifest(name="dataset_a", license="MIT"),
        LicenseManifest(name="dataset_b", license="Apache-2.0"),
    )
    assert check_compatibility(permissive)["can_publish_commercially"] is True

    non_commercial = check_compatibility((LicenseManifest(name="dataset_x", license="cc-by-nc"),))
    assert non_commercial["can_publish_commercially"] is False
    assert "cc-by-nc" in non_commercial["non_commercial_licenses"]  # type: ignore[operator]
