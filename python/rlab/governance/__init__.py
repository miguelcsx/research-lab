"""Lightweight governance helpers for project-side checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

_SECRET_TERMS = ("token", "secret", "password", "credential", "key")


@dataclass(frozen=True, slots=True)
class Assumption:
    text: str
    evidence: str | None = None


@dataclass(frozen=True, slots=True)
class Threat:
    text: str
    mitigation: str | None = None


@dataclass(frozen=True, slots=True)
class SecretHit:
    key: str
    reason: str


@dataclass(frozen=True, slots=True)
class PiiHit:
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class LicenseManifest:
    name: str
    license: str


@dataclass(frozen=True, slots=True)
class LicenseCompatibilitySummary:
    compatible: bool
    warnings: tuple[str, ...]


def redact_secrets(env: Mapping[str, str]) -> dict[str, str]:
    return {
        key: ("<redacted>" if _is_secret_key(key) else value)
        for key, value in env.items()
    }


def scan_for_secrets(text: str) -> list[SecretHit]:
    hits: list[SecretHit] = []
    for line in text.splitlines():
        key, sep, _value = line.partition("=")
        if sep and _is_secret_key(key):
            hits.append(SecretHit(key=key, reason="sensitive key name"))
    return hits


def scan_for_pii(text: str) -> list[PiiHit]:
    hits = [
        PiiHit("email", value)
        for value in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    ]
    hits.extend(
        PiiHit("ip_address", value)
        for value in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    )
    return hits


def check_compatibility(
    manifests: tuple[LicenseManifest, ...],
) -> LicenseCompatibilitySummary:
    warnings = []
    for manifest in manifests:
        license_text = manifest.license.lower()
        if "non-commercial" in license_text or "nc" == license_text:
            warnings.append(f"{manifest.name} uses a non-commercial license")
        if not license_text or license_text == "unknown":
            warnings.append(f"{manifest.name} has an unknown license")
    return LicenseCompatibilitySummary(
        compatible=not warnings, warnings=tuple(warnings)
    )


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(term in lowered for term in _SECRET_TERMS)


class LabPolicy:
    """Small project policy object for Python-side preflight checks."""

    def __init__(
        self,
        forbidden_env_patterns: tuple[str, ...] = (
            "TOKEN",
            "SECRET",
            "PASSWORD",
            "KEY",
        ),
    ) -> None:
        self.forbidden_env_patterns = forbidden_env_patterns

    def check_env(self, env: Mapping[str, str]) -> list[str]:
        return [
            key
            for key in env
            if any(pattern in key.upper() for pattern in self.forbidden_env_patterns)
        ]


__all__ = [
    "Assumption",
    "Threat",
    "LabPolicy",
    "LicenseCompatibilitySummary",
    "LicenseManifest",
    "PiiHit",
    "SecretHit",
    "check_compatibility",
    "redact_secrets",
    "scan_for_pii",
    "scan_for_secrets",
]
