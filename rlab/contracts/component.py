from pydantic import BaseModel, ConfigDict


class ComponentConstraint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str = ""


class ComponentContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_type: str = "any"
    output_type: str = "any"
    constraints: tuple[ComponentConstraint, ...] = ()
    version: str = "1.0.0"


def validate_compatibility(contract: ComponentContract, target_contract: ComponentContract) -> list[str]:
    """Return list of incompatibility messages."""
    issues: list[str] = []
    if contract.input_type != "any" and target_contract.output_type != "any":
        if contract.input_type != target_contract.output_type:
            issues.append(
                f"Type mismatch: requires {contract.input_type!r}, "
                f"target produces {target_contract.output_type!r}"
            )
    return issues
