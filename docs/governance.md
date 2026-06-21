# Governance helpers

`rlab` includes lightweight governance helpers. They are guardrails, not substitutes for legal, compliance, or security review.

## Secret scanning and redaction

Python facade:

```python
from rlab.governance import redact_secrets, scan_for_secrets

safe = redact_secrets({"HF_TOKEN": "abc", "PATH": "/usr/bin"})
hits = scan_for_secrets("HF_TOKEN=abc")
```

CLI workflows surface governance warnings through `doctor`, `lint`, and `ci` commands.

## PII scanning

```python
from rlab.governance import scan_for_pii

hits = scan_for_pii("Contact user@example.com")
```

Core scanners are intentionally conservative and cover common patterns such as email addresses, US-style phone numbers, SSNs, and IP addresses.

## Policy file

A project may include `lab.policy.toml`:

```toml
[required]
require_hypothesis = true
require_data_manifest = true
require_clean_git_for_promotion = true
require_review_for_paper = true

[forbidden]
forbidden_env_patterns = ["*_TOKEN", "*SECRET*", "*KEY*", "*PASSWORD*"]
```

Policy checks are project/CI decisions. `rlab` exposes the primitives and diagnostics.

## License manifests

```python
from rlab.governance import LicenseManifest, check_compatibility

summary = check_compatibility([
    LicenseManifest(name="corpus_a", license="MIT"),
    LicenseManifest(name="corpus_b", license="Apache-2.0"),
])
```

Known non-commercial or unknown licenses are flagged.
