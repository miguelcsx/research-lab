from pydantic import BaseModel, ConfigDict


class Assumption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    experiment: str = ""
    status: str = "active"
    run_ids: tuple[str, ...] = ()


class Threat(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    experiment: str = ""
    mitigations: tuple[str, ...] = ()


def render_validity_report(
    assumptions: tuple[Assumption, ...],
    threats: tuple[Threat, ...],
) -> str:
    lines: list[str] = ["# Validity Report\n"]
    if assumptions:
        lines.append("## Assumptions\n")
        for i, a in enumerate(assumptions, 1):
            lines.append(f"{i}. {a.text}")
        lines.append("")
    if threats:
        lines.append("## Threats to Validity\n")
        for i, t in enumerate(threats, 1):
            mitigations = ""
            if t.mitigations:
                mitigations = f" (mitigations: {'; '.join(t.mitigations)})"
            lines.append(f"{i}. {t.text}{mitigations}")
        lines.append("")
    return "\n".join(lines)


__all__ = ["Assumption", "Threat", "render_validity_report"]
