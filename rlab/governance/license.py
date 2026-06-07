from pydantic import BaseModel, ConfigDict


class LicenseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    license: str
    source: str = ""
    terms: str = ""
    commercial_allowed: bool | None = None
    redistribution_allowed: bool | None = None
    citation: str = ""
    availability: str = "available"


_COMMERCIAL_FORBIDDEN = {"cc-by-nc", "cc-by-nc-sa", "cc-by-nc-nd", "non-commercial"}
_OPEN = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "cc0", "public domain"}


def check_compatibility(manifests: tuple[LicenseManifest, ...]) -> dict[str, object]:
    """Return a compatibility summary for a set of licenses."""
    licenses = [m.license.lower() for m in manifests]
    non_commercial = [l for l in licenses if l in _COMMERCIAL_FORBIDDEN]
    unknown = [l for l in licenses if l not in _COMMERCIAL_FORBIDDEN and l not in _OPEN]
    return {
        "can_publish_commercially": len(non_commercial) == 0 and len(unknown) == 0,
        "non_commercial_licenses": non_commercial,
        "unknown_licenses": unknown,
        "total": len(manifests),
    }
