# Governance

`rlab` includes lightweight governance helpers for policies, secrets, PII, and licenses. These are not substitutes for legal or compliance review, but they help research teams avoid common mistakes.

## Project policy

Create `lab.policy.toml`:

```toml
[required]
require_hypothesis = true
require_data_manifest = true
require_clean_git_for_promotion = true
require_review_for_paper = true

[forbidden]
forbidden_env_patterns = ["*_TOKEN", "*SECRET*", "*KEY*", "*PASSWORD*"]
```

Load it:

```python
from rlab.governance.policy import LabPolicy

policy = LabPolicy.load(project_root)
violations = policy.check_env(dict(os.environ))
```

## Secret redaction

```python
from rlab.governance.secrets import redact_secrets, scan_for_secrets

safe_env = redact_secrets(os.environ)
hits = scan_for_secrets("HF_TOKEN=abc123")
```

Keys containing terms like `token`, `secret`, `key`, `password`, and `credential` are redacted unless explicitly allowlisted.

## PII scanning

```python
from rlab.governance.pii import scan_for_pii

hits = scan_for_pii("Contact user@example.com")
```

Core scanners detect common emails, US-style phone numbers, SSNs, and IP addresses. Treat this as a coarse safety net, not a full PII classifier.

## License manifests

```python
from rlab.governance.license import LicenseManifest, check_compatibility

summary = check_compatibility((
    LicenseManifest(name="dataset_a", license="MIT"),
    LicenseManifest(name="dataset_b", license="Apache-2.0"),
))
```

The compatibility helper flags known non-commercial licenses and unknown licenses.

## What governance does not enforce automatically

Core `rlab` provides primitives. Your project or CI must decide when to enforce them. For example:

```bash
rlab lint
rlab ci smoke
rlab ci reproducibility-check
```

You may add custom checks around promotion, reporting, or paper package export.

## Recommended governance workflow

Before publishing or sharing:

1. Run `rlab doctor`.
2. Run `rlab lint`.
3. Run `rlab ci reproducibility-check`.
4. Confirm runs are not stale.
5. Confirm data manifests and licenses exist.
6. Scan reports and exported artifacts for secrets.
7. Freeze the selected runs.
8. Export a reproduction package.
